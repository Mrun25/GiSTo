"""
Business (Shop) — PRD §6.1.

The shop owner's identity. owner_telegram_id is the only login mechanism
in Phase 1 (no separate upload portal — PRD §3 preamble). gst_session_token
represents the GSP-mediated OTP session used to pull GSTR-2A/2B for *this*
business only (PRD §5.3) — GiSTo never sees the owner's actual GST portal
password.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class Business(Base):
    __tablename__ = "businesses"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), unique=True, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Links the Telegram identity to the business (PRD §6.1).
    owner_telegram_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    owner_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # GSP session for 2A/2B sync. Sessions expire (hours to ~30 days) and
    # require renewal (PRD §6.1, §7.2) — re-auth flow lives in
    # app/services/gst_sync.py.
    gst_session_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    onboarding_complete: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # linked_ca_ids in the PRD is represented relationally via BusinessCALink
    # (many-to-many — PRD §2.3, §6.1).
    ca_links: Mapped[list["BusinessCALink"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    sync_logs: Mapped[list["GSTSyncLog"]] = relationship(back_populates="business", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Business {self.name} ({self.gstin})>"
