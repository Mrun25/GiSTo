import json
import httpx
from app.extraction.base import ExtractionAdapter, ExtractedInvoiceData

PROMPT = """Extract these fields from the invoice image/PDF as strict JSON,
no markdown fences, no commentary:
{"supplier_name": str|null, "supplier_gstin": str|null,
 "invoice_number": str|null, "invoice_date": "YYYY-MM-DD"|null,
 "taxable_value": number|null, "gst_amount": number|null,
 "total_amount": number|null,
 "confidence_per_field": {"<field>": 0.0-1.0, ...}}
If a GSTIN digit is unclear, lower confidence_per_field.supplier_gstin
below 0.8 rather than guessing — a wrong digit silently misattributes
the whole invoice."""

class MistralExtractionAdapter(ExtractionAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def extract(self, file_bytes: bytes, mime_type: str) -> ExtractedInvoiceData:
        import base64
        b64 = base64.b64encode(file_bytes).decode()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "pixtral-12b-2409", # Use pixtral model
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {"type": "image_url", "image_url": f"data:{mime_type};base64,{b64}"},
                        ],
                    }],
                    "response_format": {"type": "json_object"},
                },
            )
        resp.raise_for_status()
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
        confidences = data.get("confidence_per_field", {})
        overall = min(confidences.values()) if confidences else 0.5
        return ExtractedInvoiceData(
            supplier_name=data.get("supplier_name"),
            supplier_gstin=data.get("supplier_gstin"),
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            taxable_value=data.get("taxable_value"),
            gst_amount=data.get("gst_amount"),
            total_amount=data.get("total_amount"),
            overall_confidence=overall,
            confidence_per_field=confidences,
            raw_provider_response=resp.text,
        )
