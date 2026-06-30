"""
GST Sync Log — PRD §6.6. "Low priority for the very first build but cheap
to include from the start, and valuable for debugging GSP integration
issues later." Every GSP sync attempt is recorded here regardless of
outcome.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class SyncResult(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class GSTSyncLog(Base):
    __tablename__ = "gst_sync_logs"

    sync_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.business_id"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    result: Mapped[SyncResult] = mapped_column(Enum(SyncResult, name="sync_result"))
    detail: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # error message, etc.

    business: Mapped["Business"] = relationship(back_populates="sync_logs")
