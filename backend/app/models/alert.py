"""
Alert — PRD §6.5. The artifact behind the ITC Risk Alert flow (§3.3).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    REMINDER_SENT = "reminder_sent"
    RESOLVED = "resolved"


class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.business_id"), nullable=False, index=True
    )
    supplier_gstin: Mapped[str] = mapped_column(
        String(15), ForeignKey("suppliers.supplier_gstin"), nullable=False
    )
    # period as "YYYY-MM" — identifies the specific risk instance (PRD §6.5).
    period: Mapped[str] = mapped_column(String(7), nullable=False)

    amount_at_risk: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, name="alert_status"), default=AlertStatus.OPEN)

    # Internal notes a CA can add during drill-down (PRD §4.2.2).
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Snooze support for the "remind later" action (PRD §3.3).
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    business: Mapped["Business"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert {self.supplier_gstin} {self.period} ₹{self.amount_at_risk}>"
