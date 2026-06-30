import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.extraction.factory import get_extraction_adapter
from app.gsp.factory import get_gsp_adapter
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceExtractOut, InvoiceConfirmRequest, InvoiceOut
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/extract", response_model=InvoiceExtractOut)
async def extract_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """PRD §3.2 steps 1-2: owner sends a photo/PDF/screenshot; bot runs
    extraction and replies with a structured confirmation card."""
    file_bytes = await file.read()
    service = InvoiceService(db, get_extraction_adapter(), get_gsp_adapter())
    extracted, fields_requiring_review, gstin_status = await service.extract_invoice(file_bytes, file.content_type or "application/octet-stream")
    return InvoiceExtractOut(
        supplier_name=extracted.supplier_name,
        supplier_gstin=extracted.supplier_gstin,
        invoice_number=extracted.invoice_number,
        invoice_date=extracted.invoice_date,
        taxable_value=extracted.taxable_value,
        gst_amount=extracted.gst_amount,
        total_amount=extracted.total_amount,
        overall_confidence=extracted.overall_confidence,
        confidence_per_field=extracted.confidence_per_field,
        fields_requiring_review=fields_requiring_review,
        supplier_gstin_status=gstin_status,
    )


@router.post("/confirm", response_model=InvoiceOut)
def confirm_invoice(payload: InvoiceConfirmRequest, db: Session = Depends(get_db)):
    """PRD §3.2 steps 3-4: owner confirms (or corrects), invoice stored and
    linked to the supplier record."""
    service = InvoiceService(db, get_extraction_adapter(), get_gsp_adapter())
    return service.confirm_invoice(payload)


@router.get("/by-business/{business_id}", response_model=list[InvoiceOut])
def list_invoices(business_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(Invoice).filter_by(business_id=business_id).order_by(Invoice.created_at.desc()).all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice
