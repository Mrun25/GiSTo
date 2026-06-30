import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.ca import CA, BusinessCALink
from app.models.invoice import Invoice
from app.models.supplier import Supplier
from app.schemas.ca import (
    CACreateInviteRequest, CAOut, CAAcceptInviteRequest,
    PortfolioOut, SupplierFilingHistoryOut, PermissionUpdateRequest,
)
from app.schemas.invoice import InvoiceOut
from app.services.ca_service import CAService

router = APIRouter(prefix="/ca", tags=["ca"])


@router.post("/invite", response_model=CAOut)
def create_invite(payload: CACreateInviteRequest, db: Session = Depends(get_db)):
    """PRD §3.5: owner shares CA contact via the bot."""
    service = CAService(db)
    link = service.create_invite(payload.business_id, payload.ca_name, payload.ca_contact)
    return link.ca


@router.post("/invite/accept", response_model=CAOut)
def accept_invite(payload: CAAcceptInviteRequest, db: Session = Depends(get_db)):
    """PRD §4.2.3: CA accepts invite, dashboard account created."""
    service = CAService(db)
    try:
        link = service.accept_invite(payload.link_id, payload.email)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return link.ca


@router.patch("/links/{link_id}/permission")
def update_permission(link_id: uuid.UUID, payload: PermissionUpdateRequest, db: Session = Depends(get_db)):
    """PRD §4.2.3: view_only vs. can_act, set per linked business."""
    service = CAService(db)
    try:
        service.update_permission(link_id, payload.permission)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


@router.get("/{ca_id}/portfolio", response_model=PortfolioOut)
def get_portfolio(ca_id: uuid.UUID, db: Session = Depends(get_db)):
    """PRD §4.2.1: Portfolio View, the default landing screen."""
    service = CAService(db)
    return service.get_portfolio(ca_id)


@router.get("/{ca_id}/business/{business_id}/invoices", response_model=list[InvoiceOut])
def drill_down_invoices(ca_id: uuid.UUID, business_id: uuid.UUID, db: Session = Depends(get_db)):
    """PRD §4.2.2: Single-Business Drill-Down, full invoice ledger.
    (Access check against the link is omitted in this MVP for brevity —
    see README "Known simplifications".)"""
    link = db.query(BusinessCALink).filter_by(ca_id=ca_id, business_id=business_id).first()
    if not link:
        raise HTTPException(403, "No link between this CA and business")
    return db.query(Invoice).filter_by(business_id=business_id).order_by(Invoice.created_at.desc()).all()


@router.get("/{ca_id}/business/{business_id}/suppliers", response_model=list[SupplierFilingHistoryOut])
def drill_down_suppliers(ca_id: uuid.UUID, business_id: uuid.UUID, db: Session = Depends(get_db)):
    """PRD §4.2.2: supplier list with filing-status history, not just
    current period."""
    link = db.query(BusinessCALink).filter_by(ca_id=ca_id, business_id=business_id).first()
    if not link:
        raise HTTPException(403, "No link between this CA and business")
    supplier_gstins = (
        db.query(Invoice.counterparty_gstin)
        .filter(Invoice.business_id == business_id, Invoice.counterparty_gstin.isnot(None))
        .distinct()
        .all()
    )
    out = []
    for (gstin,) in supplier_gstins:
        supplier = db.get(Supplier, gstin)
        if supplier:
            out.append(SupplierFilingHistoryOut(
                supplier_gstin=supplier.supplier_gstin, legal_name=supplier.legal_name,
                risk_score=supplier.risk_score, filing_history=supplier.filing_history or [],
            ))
    return out


@router.get("/by-email/{email}", response_model=CAOut)
def get_ca_by_email(email: str, db: Session = Depends(get_db)):
    ca = db.query(CA).filter_by(email=email).first()
    if not ca:
        raise HTTPException(404, "CA not found")
    return ca
