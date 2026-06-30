import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ca import PermissionLevel, LinkStatus


class CACreateInviteRequest(BaseModel):
    business_id: uuid.UUID
    ca_name: str
    ca_contact: str


class CAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ca_id: uuid.UUID
    name: str
    contact: str
    dashboard_account_created: bool


class CAAcceptInviteRequest(BaseModel):
    link_id: uuid.UUID
    email: str


class PortfolioBusinessOut(BaseModel):
    """One row in the CA's portfolio view (PRD §4.2.1)."""
    business_id: uuid.UUID
    name: str
    itc_at_risk_current_period: float
    non_compliant_supplier_count: int
    last_invoice_sync_date: datetime | None
    permission: PermissionLevel


class PortfolioOut(BaseModel):
    businesses: list[PortfolioBusinessOut]
    total_itc_at_risk: float


class SupplierFilingHistoryOut(BaseModel):
    supplier_gstin: str
    legal_name: str | None
    risk_score: float | None
    filing_history: list[dict]


class PermissionUpdateRequest(BaseModel):
    permission: PermissionLevel
