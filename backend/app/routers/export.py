import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.invoice import Invoice

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/business/{business_id}/invoices.csv")
def export_invoices_csv(business_id: uuid.UUID, db: Session = Depends(get_db)):
    """PRD §4.2.2: export of clean invoice/ledger data (CSV/Excel) for use
    in the CA's existing filing workflow."""
    invoices = db.query(Invoice).filter_by(business_id=business_id).order_by(Invoice.invoice_date).all()
    if not invoices:
        raise HTTPException(404, "No invoices for this business")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "invoice_number", "direction", "invoice_date", "counterparty_name", "counterparty_gstin",
        "taxable_value", "gst_amount", "total_amount", "status", "itc_status",
    ])
    for inv in invoices:
        writer.writerow([
            inv.invoice_number, inv.direction.value, inv.invoice_date, inv.counterparty_name,
            inv.counterparty_gstin, inv.taxable_value, inv.gst_amount, inv.total_amount,
            inv.status.value, inv.itc_status.value,
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=invoices_{business_id}.csv"},
    )
