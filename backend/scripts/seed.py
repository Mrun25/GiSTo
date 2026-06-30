"""
Seed script — populates the DB with realistic demo data so the dashboard
and bot have something to show immediately, without waiting for real
Telegram traffic. Mirrors the PRD's own running example: an electronics
shop in Nagpur, supplier "Ravi Trading", an ITC-at-risk scenario.

Run with: python -m scripts.seed   (from backend/, with DATABASE_URL set
and the DB already migrated via `alembic upgrade head`)
"""
import asyncio
from datetime import date, datetime, timedelta

from app.core.db import SessionLocal
from app.models.business import Business
from app.models.ca import CA, BusinessCALink, PermissionLevel, LinkStatus
from app.models.supplier import Supplier, GSTINStatus
from app.models.invoice import Invoice, InvoiceDirection, InvoiceStatus, ITCStatus
from app.models.alert import Alert, AlertStatus
from app.services.risk_scoring import compute_risk_score

SUPPLIERS = [
    # (gstin, legal_name, status, filing_history)
    ("27AAACR1234A1ZP", "Ravi Trading Co.", GSTINStatus.ACTIVE, [
        {"period": "2026-02", "filed": True, "filed_on_time": True, "filed_date": "2026-03-10"},
        {"period": "2026-03", "filed": False, "filed_on_time": False, "filed_date": None},
        {"period": "2026-04", "filed": False, "filed_on_time": False, "filed_date": None},
    ]),
    ("27AAACS5678B1Z9", "Shree Electronics Distributors", GSTINStatus.ACTIVE, [
        {"period": "2026-02", "filed": True, "filed_on_time": True, "filed_date": "2026-03-09"},
        {"period": "2026-03", "filed": True, "filed_on_time": True, "filed_date": "2026-04-08"},
        {"period": "2026-04", "filed": True, "filed_on_time": False, "filed_date": "2026-05-19"},
    ]),
    ("27AABCN4321C1Z5", "Nagpur Hardware Mart", GSTINStatus.ACTIVE, [
        {"period": "2026-02", "filed": False, "filed_on_time": False, "filed_date": None},
        {"period": "2026-03", "filed": False, "filed_on_time": False, "filed_date": None},
        {"period": "2026-04", "filed": False, "filed_on_time": False, "filed_date": None},
    ]),
    ("29AAACB9988D1Z2", "Bharat Component Suppliers", GSTINStatus.ACTIVE, [
        {"period": "2026-02", "filed": True, "filed_on_time": True, "filed_date": "2026-03-07"},
        {"period": "2026-03", "filed": True, "filed_on_time": True, "filed_date": "2026-04-06"},
        {"period": "2026-04", "filed": True, "filed_on_time": True, "filed_date": "2026-05-08"},
    ]),
]

BUSINESSES = [
    {
        "owner_telegram_id": "tg_demo_5511223344",
        "name": "Sharma Electronics",
        "gstin": "27AADCS1111F1ZK",
        "state": "Maharashtra",
        "address": "Sitabuldi, Nagpur, Maharashtra",
    },
    {
        "owner_telegram_id": "tg_demo_5511223355",
        "name": "Krishna Mobile & Accessories",
        "gstin": "27AADCK2222G1ZL",
        "state": "Maharashtra",
        "address": "Itwari, Nagpur, Maharashtra",
    },
    {
        "owner_telegram_id": "tg_demo_5511223366",
        "name": "New Era Hardware",
        "gstin": "29AADCN3333H1ZM",
        "state": "Karnataka",
        "address": "Jayanagar, Bengaluru, Karnataka",
    },
]


def seed():
    db = SessionLocal()
    try:
        # --- Suppliers ---
        suppliers = {}
        for gstin, name, status, history in SUPPLIERS:
            s = db.get(Supplier, gstin)
            if not s:
                s = Supplier(supplier_gstin=gstin, legal_name=name, gstin_status=status, filing_history=history,
                             risk_score=compute_risk_score(history))
                db.add(s)
            else:
                s.filing_history = history
                s.risk_score = compute_risk_score(history)
            suppliers[gstin] = s
        db.commit()

        # --- CA ---
        ca = db.query(CA).filter_by(contact="mrunmayee.ca@example.com").first()
        if not ca:
            ca = CA(
                name="Mrunmayee & Associates",
                contact="mrunmayee.ca@example.com",
                email="mrunmayee.ca@example.com",
                dashboard_account_created=True,
            )
            db.add(ca)
            db.commit()

        businesses = []
        for b_data in BUSINESSES:
            business = db.query(Business).filter_by(owner_telegram_id=b_data["owner_telegram_id"]).first()
            if not business:
                business = Business(**b_data, onboarding_complete=True, gst_session_token="seed-session-token",
                                     token_expiry=datetime.utcnow() + timedelta(days=25))
                db.add(business)
                db.commit()
            businesses.append(business)

            link = db.query(BusinessCALink).filter_by(business_id=business.business_id, ca_id=ca.ca_id).first()
            if not link:
                link = BusinessCALink(
                    business_id=business.business_id, ca_id=ca.ca_id,
                    permission=PermissionLevel.CAN_ACT, status=LinkStatus.ACCEPTED,
                    accepted_at=datetime.utcnow(),
                )
                db.add(link)
        db.commit()

        # --- Invoices for business[0] (Sharma Electronics) — the PRD's running example ---
        sharma = businesses[0]
        existing_invoices = db.query(Invoice).filter_by(business_id=sharma.business_id).count()
        if existing_invoices == 0:
            demo_invoices = [
                # Ravi Trading — non-filer, this is the PRD's "₹12,000 at risk" example
                dict(supplier_gstin="27AAACR1234A1ZP", invoice_number="RT-0231", invoice_date=date(2026, 3, 12),
                     taxable_value=66667.00, gst_amount=12000.00, total_amount=78667.00, period_at_risk=True),
                dict(supplier_gstin="27AAACR1234A1ZP", invoice_number="RT-0255", invoice_date=date(2026, 4, 4),
                     taxable_value=50000.00, gst_amount=9000.00, total_amount=59000.00, period_at_risk=True),
                # Nagpur Hardware Mart — chronic non-filer
                dict(supplier_gstin="27AABCN4321C1Z5", invoice_number="NHM-1190", invoice_date=date(2026, 4, 18),
                     taxable_value=22000.00, gst_amount=3960.00, total_amount=25960.00, period_at_risk=True),
                # Shree Electronics — filed late but filed (verified)
                dict(supplier_gstin="27AAACS5678B1Z9", invoice_number="SED-887", invoice_date=date(2026, 4, 2),
                     taxable_value=120000.00, gst_amount=21600.00, total_amount=141600.00, period_at_risk=False),
                # Bharat Component Suppliers — reliable filer
                dict(supplier_gstin="29AAACB9988D1Z2", invoice_number="BCS-552", invoice_date=date(2026, 4, 9),
                     taxable_value=35000.00, gst_amount=6300.00, total_amount=41300.00, period_at_risk=False),
            ]
            for inv_data in demo_invoices:
                period_at_risk = inv_data.pop("period_at_risk")
                supplier_gstin = inv_data.pop("supplier_gstin")
                supplier = suppliers[supplier_gstin]
                invoice = Invoice(
                    business_id=sharma.business_id,
                    direction=InvoiceDirection.PURCHASE,
                    counterparty_name=supplier.legal_name,
                    counterparty_gstin=supplier_gstin,
                    status=InvoiceStatus.CONFIRMED_BY_OWNER,
                    itc_status=ITCStatus.AT_RISK_NOT_FILED if period_at_risk else ITCStatus.VERIFIED_FILED,
                    extraction_confidence=0.94,
                    **inv_data,
                )
                db.add(invoice)
            db.commit()

            # Alerts matching the at-risk invoices above
            alerts = [
                Alert(business_id=sharma.business_id, supplier_gstin="27AAACR1234A1ZP", period="2026-03",
                      amount_at_risk=12000.00, status=AlertStatus.OPEN),
                Alert(business_id=sharma.business_id, supplier_gstin="27AAACR1234A1ZP", period="2026-04",
                      amount_at_risk=9000.00, status=AlertStatus.OPEN),
                Alert(business_id=sharma.business_id, supplier_gstin="27AABCN4321C1Z5", period="2026-04",
                      amount_at_risk=3960.00, status=AlertStatus.OPEN),
            ]
            db.add_all(alerts)
            db.commit()

        # --- A few invoices for the other two businesses so the portfolio view isn't empty ---
        krishna = businesses[1]
        if db.query(Invoice).filter_by(business_id=krishna.business_id).count() == 0:
            inv = Invoice(
                business_id=krishna.business_id, direction=InvoiceDirection.PURCHASE,
                counterparty_name="Shree Electronics Distributors", counterparty_gstin="27AAACS5678B1Z9",
                invoice_number="SED-901", invoice_date=date(2026, 4, 11),
                taxable_value=18000.00, gst_amount=3240.00, total_amount=21240.00,
                status=InvoiceStatus.CONFIRMED_BY_OWNER, itc_status=ITCStatus.VERIFIED_FILED,
            )
            db.add(inv)
            db.commit()

        new_era = businesses[2]
        if db.query(Invoice).filter_by(business_id=new_era.business_id).count() == 0:
            inv = Invoice(
                business_id=new_era.business_id, direction=InvoiceDirection.PURCHASE,
                counterparty_name="Bharat Component Suppliers", counterparty_gstin="29AAACB9988D1Z2",
                invoice_number="BCS-310", invoice_date=date(2026, 4, 3),
                taxable_value=45000.00, gst_amount=8100.00, total_amount=53100.00,
                status=InvoiceStatus.CONFIRMED_BY_OWNER, itc_status=ITCStatus.VERIFIED_FILED,
            )
            db.add(inv)
            alert = Alert(business_id=new_era.business_id, supplier_gstin="29AAACB9988D1Z2", period="2026-02",
                           amount_at_risk=1500.00, status=AlertStatus.RESOLVED, resolved_at=datetime.utcnow())
            db.add(alert)
            db.commit()

        print("Seed complete.")
        print(f"  CA: {ca.name} ({ca.ca_id})")
        for b in businesses:
            print(f"  Business: {b.name} ({b.business_id}) — telegram_id={b.owner_telegram_id}")
        print("\nUse the CA dashboard with ca_id above. Use Telegram bot demo mode with the owner_telegram_id values above.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
