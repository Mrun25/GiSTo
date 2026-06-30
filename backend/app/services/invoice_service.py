"""
Invoice submission — PRD §3.2 (Flow: Submitting an Invoice, the core loop).

Design rule enforced here (§3.2): any field extracted with low
confidence — especially supplier_gstin — must always be surfaced to the
owner for confirmation, never auto-accepted silently. LOW_CONFIDENCE_THRESHOLD
is the line; GSTIN gets a stricter threshold than other fields because a
single wrong digit silently misattributes the entire invoice (§7.1).
"""
from sqlalchemy.orm import Session

from app.extraction.base import ExtractionAdapter, ExtractedInvoiceData
from app.gsp.base import GSPAdapter
from app.models.invoice import Invoice, InvoiceDirection, InvoiceStatus, ITCStatus
from app.models.supplier import Supplier, GSTINStatus
from app.schemas.invoice import InvoiceConfirmRequest

GENERAL_CONFIDENCE_THRESHOLD = 0.80
GSTIN_CONFIDENCE_THRESHOLD = 0.90  # stricter — see module docstring


class InvoiceService:
    def __init__(self, db: Session, extraction: ExtractionAdapter, gsp: GSPAdapter):
        self.db = db
        self.extraction = extraction
        self.gsp = gsp

    async def extract_invoice(self, file_bytes: bytes, mime_type: str) -> tuple[ExtractedInvoiceData, list[str], str | None]:
        """Step 1-2 of §3.2: run AI extraction, then determine which fields
        need mandatory owner review and check the supplier's current GSTIN
        status to show alongside the confirmation card."""
        extracted = await self.extraction.extract(file_bytes, mime_type)

        fields_requiring_review = []
        for field_name, confidence in extracted.confidence_per_field.items():
            threshold = GSTIN_CONFIDENCE_THRESHOLD if field_name == "supplier_gstin" else GENERAL_CONFIDENCE_THRESHOLD
            if confidence < threshold:
                fields_requiring_review.append(field_name)

        supplier_gstin_status = None
        if extracted.supplier_gstin:
            validation = await self.gsp.validate_gstin(extracted.supplier_gstin)
            if validation.is_valid:
                supplier_gstin_status = "active" if validation.is_active else "cancelled"

        return extracted, fields_requiring_review, supplier_gstin_status

    def _get_or_create_supplier(self, gstin: str, status: str | None, legal_name: str | None) -> Supplier:
        supplier = self.db.get(Supplier, gstin)
        if supplier:
            return supplier
        supplier = Supplier(
            supplier_gstin=gstin,
            legal_name=legal_name,
            gstin_status=GSTINStatus.ACTIVE if status != "cancelled" else GSTINStatus.CANCELLED,
            filing_history=[],
        )
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def confirm_invoice(self, payload: InvoiceConfirmRequest) -> Invoice:
        """Step 3-4 of §3.2: owner confirms (optionally after correcting a
        field); confirmed invoice is stored and linked to the supplier
        record. Only meaningful for purchase invoices does linking to the
        normalized Supplier entity matter for ITC tracking (§6.4) — sale
        invoices still get a counterparty_gstin denormalized but aren't
        forced into the suppliers table."""
        supplier_gstin = None
        if payload.direction == InvoiceDirection.PURCHASE and payload.supplier_gstin:
            supplier = self._get_or_create_supplier(payload.supplier_gstin, None, payload.supplier_name)
            supplier_gstin = supplier.supplier_gstin

        invoice = Invoice(
            business_id=payload.business_id,
            direction=payload.direction,
            counterparty_name=payload.supplier_name,
            counterparty_gstin=supplier_gstin or payload.supplier_gstin,
            invoice_number=payload.invoice_number,
            invoice_date=payload.invoice_date,
            taxable_value=payload.taxable_value,
            gst_amount=payload.gst_amount,
            total_amount=payload.total_amount,
            source_file=payload.source_file,
            extraction_confidence=payload.extraction_confidence,
            status=InvoiceStatus.CONFIRMED_BY_OWNER,
            itc_status=ITCStatus.PENDING_VERIFICATION if payload.direction == InvoiceDirection.PURCHASE else ITCStatus.VERIFIED_FILED,
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice
