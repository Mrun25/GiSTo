"""
Invoice — PRD §6.3.

itc_status is the field the entire alert system (§3.3) is built on:
pending_verification -> verified_filed, or -> at_risk_not_filed once a
GSTR-2A/2B sync (app/services/gst_sync.py) fails to find a matching
supplier filing past the grace period.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import String, DateTime, Date, Enum, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class InvoiceDirection(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"


class InvoiceStatus(str, enum.Enum):
    LOGGED = "logged"
    CONFIRMED_BY_OWNER = "confirmed_by_owner"
    DISPUTED = "disputed"


class ITCStatus(str, enum.Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED_FILED = "verified_filed"
    AT_RISK_NOT_FILED = "at_risk_not_filed"


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.business_id"), nullable=False, index=True
    )
    direction: Mapped[InvoiceDirection] = mapped_column(Enum(InvoiceDirection, name="invoice_direction"))

    # The other party on the invoice (PRD §6.3). Foreign-keyed to the
    # normalized Supplier entity (§6.4) when it's a purchase from a GSTIN
    # we've seen before; counterparty_gstin is kept denormalized too so a
    # sale-side counterparty (a customer, not necessarily a tracked Supplier)
    # doesn't force a row into the suppliers table.
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty_gstin: Mapped[str | None] = mapped_column(
        String(15), ForeignKey("suppliers.supplier_gstin"), nullable=True, index=True
    )

    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    taxable_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    gst_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Original photo/PDF retained for audit and re-verification (PRD §6.3).
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Flags low-confidence reads for mandatory owner review (PRD §3.2 design
    # rule, §6.3, §7.1). 0.0-1.0; anything below the extraction adapter's
    # threshold must be shown back to the owner, never auto-accepted.
    extraction_confidence: Mapped[float | None] = mapped_column(nullable=True)

    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.LOGGED
    )
    itc_status: Mapped[ITCStatus] = mapped_column(
        Enum(ITCStatus, name="itc_status"), default=ITCStatus.PENDING_VERIFICATION
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    business: Mapped["Business"] = relationship(back_populates="invoices")
    supplier: Mapped["Supplier | None"] = relationship(back_populates="invoices")

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number} {self.direction} itc={self.itc_status}>"
