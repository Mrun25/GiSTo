import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertStatus


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alert_id: uuid.UUID
    business_id: uuid.UUID
    supplier_gstin: str
    supplier_name: str | None = None
    period: str
    amount_at_risk: float
    status: AlertStatus
    notes: str | None
    created_at: datetime


class AlertActionRequest(BaseModel):
    action: str  # "send_reminder" | "snooze" | "mark_resolved"
    snooze_days: int | None = None
    note: str | None = None


class ReminderDraftOut(BaseModel):
    """Drafted message shown for owner approval before sending (PRD §3.3,
    §7.1 — GiSTo never contacts a third party without explicit per-instance
    confirmation)."""
    alert_id: uuid.UUID
    supplier_name: str | None
    draft_message: str


class DigestOut(BaseModel):
    period_label: str
    invoices_logged_purchases: int
    invoices_logged_sales: int
    suppliers_non_compliant: int
    total_itc_at_risk: float
    total_itc_secured: float
