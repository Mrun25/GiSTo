import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.gsp.factory import get_gsp_adapter
from app.models.business import Business
from app.schemas.business import (
    BusinessOut, GSTINValidateRequest, GSTINValidateOut,
    OTPStartOut, OTPCompleteRequest, OTPCompleteOut,
)
from app.schemas.ca import SupplierFilingHistoryOut
from app.models.supplier import Supplier
from app.models.invoice import Invoice
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("/validate-gstin", response_model=GSTINValidateOut)
async def validate_gstin(payload: GSTINValidateRequest, db: Session = Depends(get_db)):
    """PRD §3.1 step 2."""
    service = OnboardingService(db, get_gsp_adapter())
    result = await service.validate_gstin(payload.gstin)
    return GSTINValidateOut(**result.__dict__)


@router.post("", response_model=BusinessOut)
async def create_business(owner_telegram_id: str, gstin: str, db: Session = Depends(get_db)):
    service = OnboardingService(db, get_gsp_adapter())
    validation = await service.validate_gstin(gstin)
    if not validation.is_valid:
        raise HTTPException(400, "Invalid GSTIN format")
    business = service.get_or_create_business(owner_telegram_id, gstin, validation)
    return business


@router.post("/{business_id}/otp/start", response_model=OTPStartOut)
async def start_otp(business_id: uuid.UUID, db: Session = Depends(get_db)):
    """PRD §3.1 step 3: secure authorization link for GSP-hosted OTP login."""
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    service = OnboardingService(db, get_gsp_adapter())
    url = await service.start_otp_authorization(business)
    return OTPStartOut(authorization_url=url)


@router.post("/otp/complete", response_model=OTPCompleteOut)
async def complete_otp(payload: OTPCompleteRequest, db: Session = Depends(get_db)):
    """PRD §3.1 step 4."""
    business = db.get(Business, payload.business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    service = OnboardingService(db, get_gsp_adapter())
    await service.complete_otp_authorization(business, payload.otp_reference)
    return OTPCompleteOut(success=True, token_expiry=business.token_expiry.date())


@router.get("/by-telegram/{telegram_id}", response_model=BusinessOut)
def get_by_telegram(telegram_id: str, db: Session = Depends(get_db)):
    business = db.query(Business).filter_by(owner_telegram_id=telegram_id).first()
    if not business:
        raise HTTPException(404, "Business not found")
    return business


@router.get("", response_model=list[BusinessOut])
def list_onboarded_businesses(db: Session = Depends(get_db)):
    """Used by the bot's proactive notifier sweep (PRD §3.3/§3.4) to find
    every business it should check for new alerts/digests. Internal/bot-
    to-backend use only — not exposed to the CA dashboard."""
    return db.query(Business).filter_by(onboarding_complete=True).all()


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
    return business


@router.get("/{business_id}/suppliers", response_model=list[SupplierFilingHistoryOut])
def get_business_suppliers(business_id: uuid.UUID, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")
        
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
