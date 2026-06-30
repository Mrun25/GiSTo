"""
CA / Accountant — PRD §6.2, and the link table that realizes the
many-to-many relationship described in PRD §2.3 and §4.2.3.

A plain association table wouldn't be enough here because the
relationship itself carries data: permission_per_business (view_only vs.
can_act) and the invite/accept lifecycle (PRD §4.2.3). So BusinessCALink
is a first-class model, not just a join table.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class PermissionLevel(str, enum.Enum):
    VIEW_ONLY = "view_only"
    CAN_ACT = "can_act"


class LinkStatus(str, enum.Enum):
    INVITED = "invited"      # owner shared CA contact via bot (PRD §3.5), no dashboard account yet
    ACCEPTED = "accepted"    # CA accepted invite, dashboard account created/linked (PRD §4.2.3)
    REVOKED = "revoked"


class CA(Base):
    __tablename__ = "cas"

    ca_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact: Mapped[str] = mapped_column(String(255), nullable=False)  # phone or email used for invite
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    # Set once the CA actually accepts an invite and creates a dashboard login
    # (PRD §4.2.3). Until then the CA row may exist purely from §3.5 capture.
    dashboard_account_created: Mapped[bool] = mapped_column(default=False)
    telegram_id_for_notifications: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    business_links: Mapped[list["BusinessCALink"]] = relationship(
        back_populates="ca", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CA {self.name}>"


class BusinessCALink(Base):
    """
    The many-to-many edge between Business and CA (PRD §2.3: "one CA may
    manage many businesses; in rare cases a business may have more than
    one accountant relationship"). permission_per_business lives here,
    per-link, exactly as PRD §4.2.3 and §6.2 specify.
    """
    __tablename__ = "business_ca_links"
    __table_args__ = (UniqueConstraint("business_id", "ca_id", name="uq_business_ca"),)

    link_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.business_id"), nullable=False
    )
    ca_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cas.ca_id"), nullable=False)

    permission: Mapped[PermissionLevel] = mapped_column(
        Enum(PermissionLevel, name="permission_level"), default=PermissionLevel.VIEW_ONLY
    )
    status: Mapped[LinkStatus] = mapped_column(Enum(LinkStatus, name="link_status"), default=LinkStatus.INVITED)

    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped["Business"] = relationship(back_populates="ca_links")
    ca: Mapped["CA"] = relationship(back_populates="business_links")
