import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class BusinessCreate(BaseModel):
    owner_telegram_id: str
    gstin: str


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_id: uuid.UUID
    name: str
    gstin: str
    state: str | None
    owner_telegram_id: str
    onboarding_complete: bool


class GSTINValidateRequest(BaseModel):
    gstin: str


class GSTINValidateOut(BaseModel):
    gstin: str
    is_valid: bool
    is_active: bool
    legal_name: str | None
    state: str | None


class OTPStartOut(BaseModel):
    authorization_url: str


class OTPCompleteRequest(BaseModel):
    business_id: uuid.UUID
    otp_reference: str


class OTPCompleteOut(BaseModel):
    success: bool
    token_expiry: date
