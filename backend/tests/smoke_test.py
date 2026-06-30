"""
End-to-end smoke test for the core loop, run against SQLite in-memory
(no Postgres/docker needed for this check). Exercises:
  PRD §3.1 onboarding -> §3.2 invoice submission -> §3.3 ITC risk alert
  -> §3.4 digest -> §3.5 CA invite -> §4.2.1 portfolio view -> §8.3 risk scoring

Run with: python -m tests.smoke_test  (from backend/ with deps installed)
"""
import asyncio
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app import models
from app.models.business import Business
from app.models.invoice import InvoiceDirection
from app.gsp.mock_gsp import MockGSPAdapter
from app.extraction.mock_extraction import MockExtractionAdapter
from app.services.onboarding_service import OnboardingService
from app.services.invoice_service import InvoiceService
from app.services.gst_sync import GSTSyncService
from app.services.alert_service import AlertService
from app.services.ca_service import CAService
from app.services.risk_scoring import RiskScoringService
from app.schemas.invoice import InvoiceConfirmRequest


async def main():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    gsp = MockGSPAdapter()
    extraction = MockExtractionAdapter()

    # --- §3.1 Onboarding ---
    onboarding = OnboardingService(db, gsp)
    validation = await onboarding.validate_gstin("27AAACR1234A1ZP")
    assert validation.is_valid, "GSTIN should validate"
    business = onboarding.get_or_create_business("tg_12345", "27AAACR1234A1ZP", validation)
    auth_url = await onboarding.start_otp_authorization(business)
    assert auth_url.startswith("https://")
    await onboarding.complete_otp_authorization(business, "otp-ref-1")
    assert business.onboarding_complete
    print("✓ Onboarding flow OK — business:", business.name, business.business_id)

    # --- §3.2 Invoice submission, including a forced AT_RISK case ---
    invoice_service = InvoiceService(db, extraction, gsp)
    extracted, review_fields, gstin_status = await invoice_service.extract_invoice(b"fake-image-bytes", "image/jpeg")
    print(f"✓ Extraction OK — supplier={extracted.supplier_name}, review_fields={review_fields}, gstin_status={gstin_status}")

    from datetime import date
    payload = InvoiceConfirmRequest(
        business_id=business.business_id,
        direction=InvoiceDirection.PURCHASE,
        supplier_name="Ravi Trading Co.",
        supplier_gstin="27AAACR1234A1ZP",  # reuse a deterministic GSTIN we can control filing for
        invoice_number="INV-001",
        invoice_date=date(2026, 4, 15),
        taxable_value=100000.0,
        gst_amount=18000.0,
        total_amount=118000.0,
    )
    invoice = invoice_service.confirm_invoice(payload)
    assert invoice.itc_status.value == "pending_verification"
    print("✓ Invoice confirmed and linked to supplier — itc_status:", invoice.itc_status.value)

    # Second invoice, same supplier, for a period the mock GSP deterministically
    # marks as NOT FILED — this exercises the actual alert-creation path,
    # which is the core value proposition of the whole product.
    risky_payload = InvoiceConfirmRequest(
        business_id=business.business_id,
        direction=InvoiceDirection.PURCHASE,
        supplier_name="Ravi Trading Co.",
        supplier_gstin="27AAACR1234A1ZP",
        invoice_number="INV-002",
        invoice_date=date(2026, 3, 10),
        taxable_value=66667.0,
        gst_amount=12000.0,
        total_amount=78667.0,
    )
    risky_invoice = invoice_service.confirm_invoice(risky_payload)

    # --- §3.3 ITC Risk Alert: force the sync past the grace period by
    # monkeypatching "now" via the service's grace-period check window.
    sync_service = GSTSyncService(db, gsp)
    # Period 2026-04 due date + grace is in the past relative to "today"
    # only if today is well after; force it true directly for the test.
    sync_service._is_past_grace_period = lambda period: True  # noqa: SLF001 test override
    result = await sync_service.sync_business_period(business, "2026-04")
    print("✓ GST sync ran (2026-04):", result)
    assert result["checked"] == 1

    risky_result = await sync_service.sync_business_period(business, "2026-03")
    print("✓ GST sync ran (2026-03, expect at_risk):", risky_result)
    assert risky_result["at_risk"] == 1, "Expected the 2026-03 invoice to be flagged at-risk"
    assert len(risky_result["alerts_created"]) == 1, "Expected exactly one new Alert to be created"

    from app.models.alert import Alert
    alerts = db.query(Alert).filter_by(business_id=business.business_id).all()
    print(f"✓ Alerts in DB after sync: {len(alerts)} -> statuses: {[a.status.value for a in alerts]}")

    # --- §3.3 reminder draft + action handling ---
    alert_service = AlertService(db)
    if alerts:
        draft = alert_service.draft_reminder(alerts[0])
        assert "Hi, this is a reminder" in draft.draft_message
        print("✓ Reminder draft generated (not sent automatically):", draft.draft_message[:60], "...")
        alert_service.snooze(alerts[0], 7)
        assert alerts[0].snoozed_until is not None
        print("✓ Snooze works")

    # --- §3.4 Digest ---
    digest = alert_service.build_digest(business.business_id, "April 2026")
    print("✓ Digest:", digest)

    # --- §3.5 / §4.2 CA invite + portfolio ---
    ca_service = CAService(db)
    link = ca_service.create_invite(business.business_id, "Mrunmayee & Co", "mrunmayee@example.com")
    assert link.status.value == "invited"
    accepted = ca_service.accept_invite(link.link_id, "mrunmayee@example.com")
    assert accepted.status.value == "accepted"
    print("✓ CA invite + accept flow OK")

    portfolio = ca_service.get_portfolio(accepted.ca_id)
    print("✓ Portfolio view:", portfolio)
    assert len(portfolio.businesses) == 1

    # --- §8.3 Risk scoring ---
    risk_service = RiskScoringService(db)
    updated = risk_service.recompute_all()
    print(f"✓ Risk scoring recomputed for {updated} supplier(s)")
    from app.models.supplier import Supplier
    supplier = db.get(Supplier, "27AAACR1234A1ZP")
    print("✓ Supplier risk_score:", supplier.risk_score, "filing_history:", supplier.filing_history)

    db.close()
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
