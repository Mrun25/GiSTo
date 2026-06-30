"""
GST sync + ITC matching — PRD §3.3 (Flow: ITC Risk Alert) and §5.3.

This is the core hypothesis the whole product validates (§8.1 goal):
for every purchase invoice logged for a period, check whether the
supplier's GSTR-2A/2B filing has appeared past the grace period. If not,
raise an Alert naming the supplier, period, and exact rupee amount at risk.

filing_grace_period_days (default 11, configurable) exists because GSTR-1
filing has a statutory due date — flagging "not filed" before that date
has even passed would be a false alarm, not a real risk.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.gsp.base import GSPAdapter
from app.gsp.mock_gsp import MockGSPAdapter
from app.models.alert import Alert, AlertStatus
from app.models.business import Business
from app.models.invoice import Invoice, InvoiceDirection, ITCStatus
from app.models.supplier import Supplier
from app.models.sync_log import GSTSyncLog, SyncResult


class GSTSyncService:
    def __init__(self, db: Session, gsp: GSPAdapter):
        self.db = db
        self.gsp = gsp
        self.settings = get_settings()

    def _is_past_grace_period(self, period: str) -> bool:
        year, month = (int(x) for x in period.split("-"))
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        due_date = datetime(next_year, next_month, 11) + timedelta(days=self.settings.filing_grace_period_days)
        return datetime.utcnow() >= due_date

    async def sync_business_period(self, business: Business, period: str) -> dict:
        """
        Runs one GSTR-2A/2B sync for a business for one period (PRD §3.3
        trigger: "a scheduled GSTR-2A/2B sync"). For every purchase invoice
        logged in that period, ask the GSP whether the supplier filed.
        Generates/updates Alerts for non-filers and records a GSTSyncLog
        row regardless of outcome (PRD §6.6).
        """
        result_summary = {"checked": 0, "at_risk": 0, "verified": 0, "alerts_created": []}

        if not self._is_past_grace_period(period):
            # Too early to judge non-filing yet for this period.
            return result_summary

        purchase_invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.business_id == business.business_id,
                Invoice.direction == InvoiceDirection.PURCHASE,
                Invoice.counterparty_gstin.isnot(None),
            )
            .all()
        )
        # Only invoices dated within this period are relevant to this sync.
        period_invoices = [
            inv for inv in purchase_invoices
            if inv.invoice_date and f"{inv.invoice_date.year:04d}-{inv.invoice_date.month:02d}" == period
        ]

        try:
            for invoice in period_invoices:
                result_summary["checked"] += 1
                record = await self._check_supplier_filed(invoice.counterparty_gstin, period)

                self._update_supplier_filing_history(invoice.counterparty_gstin, record)

                if record.filed:
                    invoice.itc_status = ITCStatus.VERIFIED_FILED
                    result_summary["verified"] += 1
                    self._resolve_alert_if_open(business.business_id, invoice.counterparty_gstin, period)
                else:
                    invoice.itc_status = ITCStatus.AT_RISK_NOT_FILED
                    result_summary["at_risk"] += 1
                    alert = self._create_or_update_alert(business, invoice, period)
                    if alert:
                        result_summary["alerts_created"].append(str(alert.alert_id))

            self.db.commit()
            self.db.add(GSTSyncLog(
                business_id=business.business_id, period=period,
                result=SyncResult.SUCCESS,
                detail=f"checked={result_summary['checked']} at_risk={result_summary['at_risk']}",
            ))
            self.db.commit()
        except Exception as exc:  # noqa: BLE001 — log and re-raise for the caller/scheduler to handle
            self.db.add(GSTSyncLog(
                business_id=business.business_id, period=period,
                result=SyncResult.FAILURE, detail=str(exc),
            ))
            self.db.commit()
            raise

        return result_summary

    async def _check_supplier_filed(self, supplier_gstin: str, period: str):
        # The mock adapter exposes a deterministic per-supplier-period verdict
        # directly (see MockGSPAdapter docstring); a real GSP would instead
        # return the full 2A/2B for the business and we'd diff it here.
        if isinstance(self.gsp, MockGSPAdapter):
            return self.gsp.supplier_filed_for_period(supplier_gstin, period)
        records = await self.gsp.fetch_2a_2b(business_gstin="", session_token="", period=period)
        match = next((r for r in records if r.supplier_gstin == supplier_gstin), None)
        if match:
            return match
        from app.gsp.base import FilingRecord
        return FilingRecord(supplier_gstin=supplier_gstin, period=period, filed=False, filed_on_time=False, filed_date=None, taxable_value_reported=None)

    def _update_supplier_filing_history(self, supplier_gstin: str, record) -> None:
        supplier = self.db.get(Supplier, supplier_gstin)
        if not supplier:
            return
        history = list(supplier.filing_history or [])
        history = [h for h in history if h.get("period") != record.period]
        history.append({
            "period": record.period,
            "filed_on_time": record.filed_on_time,
            "filed_date": record.filed_date.isoformat() if record.filed_date else None,
            "filed": record.filed,
        })
        supplier.filing_history = history
        self.db.commit()

    def _create_or_update_alert(self, business: Business, invoice: Invoice, period: str) -> Alert | None:
        existing = (
            self.db.query(Alert)
            .filter_by(business_id=business.business_id, supplier_gstin=invoice.counterparty_gstin, period=period)
            .filter(Alert.status != AlertStatus.RESOLVED)
            .first()
        )
        amount = float(invoice.gst_amount or 0)
        if existing:
            existing.amount_at_risk = float(existing.amount_at_risk) + amount
            return None  # not newly created, just topped up
        alert = Alert(
            business_id=business.business_id,
            supplier_gstin=invoice.counterparty_gstin,
            period=period,
            amount_at_risk=amount,
            status=AlertStatus.OPEN,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def _resolve_alert_if_open(self, business_id, supplier_gstin: str, period: str) -> None:
        alert = (
            self.db.query(Alert)
            .filter_by(business_id=business_id, supplier_gstin=supplier_gstin, period=period)
            .filter(Alert.status != AlertStatus.RESOLVED)
            .first()
        )
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            self.db.commit()
