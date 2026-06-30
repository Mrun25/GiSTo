import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.invoice import InvoiceDirection, InvoiceStatus, ITCStatus


class InvoiceExtractOut(BaseModel):
    """Returned right after the bot uploads a file — the 'structured
    confirmation card' shown back to the owner (PRD §3.2)."""
    supplier_name: str | None
    supplier_gstin: str | None
    invoice_number: str | None
    invoice_date: date | None
    taxable_value: float | None
    gst_amount: float | None
    total_amount: float | None
    overall_confidence: float
    confidence_per_field: dict[str, float]
    fields_requiring_review: list[str]  # confidence below threshold -> must show owner, never auto-accept
    supplier_gstin_status: str | None  # "active" | "cancelled" | None if not yet checked


class InvoiceConfirmRequest(BaseModel):
    business_id: uuid.UUID
    direction: InvoiceDirection
    supplier_name: str | None = None
    supplier_gstin: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    taxable_value: float | None = None
    gst_amount: float | None = None
    total_amount: float | None = None
    source_file: str | None = None
    extraction_confidence: float | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    invoice_id: uuid.UUID
    business_id: uuid.UUID
    direction: InvoiceDirection
    counterparty_name: str | None
    counterparty_gstin: str | None
    invoice_number: str | None
    invoice_date: date | None
    taxable_value: float | None
    gst_amount: float | None
    total_amount: float | None
    status: InvoiceStatus
    itc_status: ITCStatus
    created_at: datetime
