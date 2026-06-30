"""
CA invite (PRD §3.5) and Phase 2 dashboard support (PRD §4.2).
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertStatus
from app.models.business import Business
from app.models.ca import CA, BusinessCALink, LinkStatus, PermissionLevel
from app.models.invoice import Invoice
from app.schemas.ca import PortfolioBusinessOut, PortfolioOut


class CAService:
    def __init__(self, db: Session):
        self.db = db

    def create_invite(self, business_id: uuid.UUID, ca_name: str, ca_contact: str) -> BusinessCALink:
        """PRD §3.5: owner shares a CA's contact info via the bot -> bot
        sends the CA an invite link. Captured/stored even before the
        dashboard exists (Phase 1), so Phase 2 has no onboarding backlog."""
        ca = self.db.query(CA).filter_by(contact=ca_contact).first()
        if not ca:
            ca = CA(name=ca_name, contact=ca_contact)
            self.db.add(ca)
            self.db.commit()
            self.db.refresh(ca)

        existing_link = self.db.query(BusinessCALink).filter_by(business_id=business_id, ca_id=ca.ca_id).first()
        if existing_link:
            return existing_link

        link = BusinessCALink(business_id=business_id, ca_id=ca.ca_id, status=LinkStatus.INVITED)
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def accept_invite(self, link_id: uuid.UUID, email: str) -> BusinessCALink:
        """PRD §4.2.3: CA accepts and creates a dashboard login -> link established."""
        link = self.db.get(BusinessCALink, link_id)
        if not link:
            raise ValueError("Invite not found")
        link.status = LinkStatus.ACCEPTED
        link.accepted_at = datetime.utcnow()
        link.ca.dashboard_account_created = True
        link.ca.email = email
        self.db.commit()
        self.db.refresh(link)
        return link

    def update_permission(self, link_id: uuid.UUID, permission: PermissionLevel) -> BusinessCALink:
        """PRD §4.2.3: each business-CA link has a permission level."""
        link = self.db.get(BusinessCALink, link_id)
        if not link:
            raise ValueError("Link not found")
        link.permission = permission
        self.db.commit()
        self.db.refresh(link)
        return link

    def get_portfolio(self, ca_id: uuid.UUID) -> PortfolioOut:
        """PRD §4.2.1: Portfolio View — default landing screen. All linked
        businesses with name, current-period ITC at risk, non-compliant
        supplier count, last sync date; sortable by risk; single aggregate
        figure for the whole portfolio."""
        links = (
            self.db.query(BusinessCALink)
            .filter_by(ca_id=ca_id, status=LinkStatus.ACCEPTED)
            .all()
        )
        rows = []
        for link in links:
            business = link.business
            at_risk = (
                self.db.query(func.coalesce(func.sum(Alert.amount_at_risk), 0))
                .filter(Alert.business_id == business.business_id, Alert.status != AlertStatus.RESOLVED)
                .scalar() or 0
            )
            non_compliant = (
                self.db.query(func.count(func.distinct(Alert.supplier_gstin)))
                .filter(Alert.business_id == business.business_id, Alert.status != AlertStatus.RESOLVED)
                .scalar() or 0
            )
            last_invoice = (
                self.db.query(func.max(Invoice.created_at))
                .filter(Invoice.business_id == business.business_id)
                .scalar()
            )
            rows.append(PortfolioBusinessOut(
                business_id=business.business_id,
                name=business.name,
                itc_at_risk_current_period=float(at_risk),
                non_compliant_supplier_count=non_compliant,
                last_invoice_sync_date=last_invoice,
                permission=link.permission,
            ))
        # Sortable/filterable by risk, highest exposure first by default (§4.2.1).
        rows.sort(key=lambda r: r.itc_at_risk_current_period, reverse=True)
        total = sum(r.itc_at_risk_current_period for r in rows)
        return PortfolioOut(businesses=rows, total_itc_at_risk=total)
