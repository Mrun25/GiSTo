"""
Alert actions (PRD §3.3) and the weekly/on-demand digest (PRD §3.4).
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.alert import Alert, AlertStatus
from app.models.invoice import Invoice, InvoiceDirection, ITCStatus
from app.models.supplier import Supplier
from app.schemas.alert import DigestOut, ReminderDraftOut


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def draft_reminder(self, alert: Alert) -> ReminderDraftOut:
        """PRD §3.3: bot shows the drafted message for owner approval before
        sending — GiSTo never contacts a supplier without explicit,
        per-instance owner confirmation (also §7.1)."""
        supplier = self.db.get(Supplier, alert.supplier_gstin)
        supplier_name = supplier.legal_name if supplier else alert.supplier_gstin
        message = (
            f"Hi, this is a reminder from {supplier_name}'s buyer regarding GST filing. "
            f"Our records show your GSTR-1/3B for {alert.period} hasn't appeared in our GSTR-2A/2B yet. "
            f"This is affecting our Input Tax Credit of approximately ₹{alert.amount_at_risk:,.2f}. "
            f"Could you please confirm your filing status for this period at your earliest convenience? Thank you."
        )
        return ReminderDraftOut(alert_id=alert.alert_id, supplier_name=supplier_name, draft_message=message)

    def mark_reminder_sent(self, alert: Alert) -> None:
        alert.status = AlertStatus.REMINDER_SENT
        self.db.commit()

    def snooze(self, alert: Alert, days: int) -> None:
        alert.snoozed_until = datetime.utcnow() + timedelta(days=days)
        self.db.commit()

    def mark_resolved(self, alert: Alert, note: str | None = None) -> None:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        if note:
            alert.notes = (alert.notes + "\n" if alert.notes else "") + note
        self.db.commit()

    def build_digest(self, business_id, period_label: str) -> DigestOut:
        """PRD §3.4: weekly automatic digest or on-demand /summary."""
        purchases = (
            self.db.query(func.count(Invoice.invoice_id))
            .filter(Invoice.business_id == business_id, Invoice.direction == InvoiceDirection.PURCHASE)
            .scalar() or 0
        )
        sales = (
            self.db.query(func.count(Invoice.invoice_id))
            .filter(Invoice.business_id == business_id, Invoice.direction == InvoiceDirection.SALE)
            .scalar() or 0
        )
        non_compliant_suppliers = (
            self.db.query(func.count(func.distinct(Alert.supplier_gstin)))
            .filter(Alert.business_id == business_id, Alert.status != AlertStatus.RESOLVED)
            .scalar() or 0
        )
        at_risk = (
            self.db.query(func.coalesce(func.sum(Alert.amount_at_risk), 0))
            .filter(Alert.business_id == business_id, Alert.status != AlertStatus.RESOLVED)
            .scalar() or 0
        )
        secured = (
            self.db.query(func.coalesce(func.sum(Invoice.gst_amount), 0))
            .filter(
                Invoice.business_id == business_id,
                Invoice.direction == InvoiceDirection.PURCHASE,
                Invoice.itc_status == ITCStatus.VERIFIED_FILED,
            )
            .scalar() or 0
        )
        return DigestOut(
            period_label=period_label,
            invoices_logged_purchases=purchases,
            invoices_logged_sales=sales,
            suppliers_non_compliant=non_compliant_suppliers,
            total_itc_at_risk=float(at_risk),
            total_itc_secured=float(secured),
        )
