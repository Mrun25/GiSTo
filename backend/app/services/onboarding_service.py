"""
Onboarding — PRD §3.1 (Flow: Shop Owner Onboarding).
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.gsp.base import GSPAdapter, GSTINValidationResult
from app.models.business import Business


class OnboardingService:
    def __init__(self, db: Session, gsp: GSPAdapter):
        self.db = db
        self.gsp = gsp

    async def validate_gstin(self, gstin: str) -> GSTINValidationResult:
        """Step 2 of §3.1: bot validates the GSTIN via GSP API, shows back
        registered business name/state for owner confirmation."""
        return await self.gsp.validate_gstin(gstin)

    def get_or_create_business(self, owner_telegram_id: str, gstin: str, validation: GSTINValidationResult) -> Business:
        existing = self.db.query(Business).filter_by(owner_telegram_id=owner_telegram_id).first()
        if existing:
            return existing
        business = Business(
            owner_telegram_id=owner_telegram_id,
            gstin=gstin,
            name=validation.legal_name or "Unnamed Business",
            state=validation.state,
        )
        self.db.add(business)
        self.db.commit()
        self.db.refresh(business)
        return business

    async def start_otp_authorization(self, business: Business) -> str:
        """Step 3 of §3.1: sends a secure GSP-hosted OTP login link.
        GiSTo never sees the owner's GST portal password."""
        return await self.gsp.start_otp_session(business.gstin)

    async def complete_otp_authorization(self, business: Business, otp_reference: str) -> None:
        """Step 4 of §3.1: owner completes OTP, bot stores the resulting
        session token/expiry and marks onboarding complete."""
        token, expiry = await self.gsp.complete_otp_session(business.gstin, otp_reference)
        business.gst_session_token = token
        business.token_expiry = datetime.combine(expiry, datetime.min.time())
        business.onboarding_complete = True
        self.db.commit()
