"""
Supplier (Counterparty, Normalized) — PRD §6.4.

The PRD is explicit that this is the most important structural decision
in the data model (§6 preamble): Supplier is its own entity, keyed by
GSTIN, shared across every business on GiSTo — not a field copied onto
each invoice. That's what makes Phase 3 aggregate risk scoring possible
without a data migration later.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import String, DateTime, Enum, Float, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class GSTINStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class Supplier(Base):
    __tablename__ = "suppliers"

    # supplier_gstin is the primary key per PRD §6.4 — "shared across all
    # businesses' data on GiSTo". Using the natural key directly (rather
    # than a surrogate id) is what makes the "same supplier across many
    # businesses" join trivial in Phase 3.
    supplier_gstin: Mapped[str] = mapped_column(String(15), primary_key=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    gstin_status: Mapped[GSTINStatus] = mapped_column(
        Enum(GSTINStatus, name="gstin_status"), default=GSTINStatus.ACTIVE
    )

    # filing_history: List of {period, filed_on_time, filed_date} as specified
    # in PRD §6.4. Stored as JSON rather than a child table for Phase 1
    # simplicity; promote to a proper table if query patterns demand it later.
    filing_history: Mapped[list] = mapped_column(JSON, default=list)

    # risk_score: Derived, e.g. % of last 6 periods filed late or not at all
    # (PRD §6.4). Recomputed by app/services/risk_scoring.py (Phase 3 logic,
    # but the column exists from Phase 1 so no migration is needed later).
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_gstin_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoices: Mapped[list["Invoice"]] = relationship(back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier {self.supplier_gstin} risk={self.risk_score}>"
