"""
Mock extraction adapter — returns plausible, deterministic structured data
without calling any LLM, so the core loop (PRD §3.2) is demoable with zero
API keys. Swap to Mistral (or Claude) by setting EXTRACTION_PROVIDER and
adding the corresponding adapter — see README.md in this folder.
"""
import hashlib
import random
from datetime import date, timedelta

from app.extraction.base import ExtractionAdapter, ExtractedInvoiceData

_SAMPLE_SUPPLIERS = [
    ("Ravi Trading Co.", "27AAACR1234A1ZP"),
    ("Shree Electronics Distributors", "27AAACS5678B1Z9"),
    ("Nagpur Hardware Mart", "27AABCN4321C1Z5"),
    ("Bharat Component Suppliers", "29AAACB9988D1Z2"),
    ("Om Sai Cables & Wires", "27AAFCO1122E1Z6"),
]


class MockExtractionAdapter(ExtractionAdapter):
    async def extract(self, file_bytes: bytes, mime_type: str) -> ExtractedInvoiceData:
        # Deterministic-but-varied: hash the file content so re-uploading
        # the same demo file always yields the same extracted invoice.
        seed = int(hashlib.sha256(file_bytes[:4096] or b"empty").hexdigest(), 16)
        rnd = random.Random(seed)

        name, gstin = rnd.choice(_SAMPLE_SUPPLIERS)
        taxable_value = round(rnd.uniform(2000, 80000), 2)
        gst_rate = rnd.choice([0.05, 0.12, 0.18, 0.28])
        gst_amount = round(taxable_value * gst_rate, 2)
        total = round(taxable_value + gst_amount, 2)
        inv_date = date.today() - timedelta(days=rnd.randint(1, 45))

        # Occasionally simulate a low-confidence GSTIN read (a smudged digit)
        # to exercise the mandatory-review path from PRD §3.2.
        gstin_confidence = 0.97 if seed % 5 != 0 else 0.61
        overall = min(gstin_confidence, rnd.uniform(0.85, 0.99))

        return ExtractedInvoiceData(
            supplier_name=name,
            supplier_gstin=gstin,
            invoice_number=f"INV-{seed % 100000:05d}",
            invoice_date=inv_date.isoformat(),
            taxable_value=taxable_value,
            gst_amount=gst_amount,
            total_amount=total,
            overall_confidence=overall,
            confidence_per_field={
                "supplier_gstin": gstin_confidence,
                "invoice_number": 0.95,
                "invoice_date": 0.92,
                "taxable_value": 0.94,
                "gst_amount": 0.94,
            },
            raw_provider_response="mock-extraction-no-llm-call",
        )
