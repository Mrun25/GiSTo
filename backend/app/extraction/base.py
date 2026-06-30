"""
Invoice extraction adapter interface — PRD §3.2, §5.4.

The PRD's suggested stack names Claude (multimodal/vision) for this step,
prompted for structured JSON output (§5.4). This interface is intentionally
provider-agnostic so a Mistral integration (vision-capable Pixtral models
support the same "image/PDF in, structured JSON out" shape) can be dropped
in by adding one adapter file + a factory branch — see README.md in this
folder for the exact steps.

Per the design rule in PRD §3.2: any field extracted with low confidence —
especially GSTIN, since one wrong digit silently misattributes the whole
invoice — must come back with a confidence score low enough to force
mandatory owner review. confidence_per_field carries that signal.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedInvoiceData:
    supplier_name: str | None
    supplier_gstin: str | None
    invoice_number: str | None
    invoice_date: str | None  # ISO "YYYY-MM-DD"
    taxable_value: float | None
    gst_amount: float | None
    total_amount: float | None

    # Overall confidence (0.0-1.0) and per-field confidence, so the bot can
    # decide which individual fields need explicit owner confirmation rather
    # than blanket-flagging the whole invoice (PRD §3.2 design rule).
    overall_confidence: float = 0.0
    confidence_per_field: dict[str, float] = field(default_factory=dict)

    raw_provider_response: str | None = None  # kept for audit/debugging


class ExtractionAdapter(ABC):
    @abstractmethod
    async def extract(self, file_bytes: bytes, mime_type: str) -> ExtractedInvoiceData:
        """Take a photo/PDF/screenshot of an invoice and return structured
        fields plus confidence scores (PRD §3.2)."""
        ...
