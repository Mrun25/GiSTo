import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.extraction.base import ExtractionAdapter, ExtractedInvoiceData


class InvoiceSchema(BaseModel):
    supplier_name: str | None = Field(description="Name of the supplier")
    supplier_gstin: str | None = Field(description="15-character GSTIN of the supplier")
    invoice_number: str | None = Field(description="Invoice number")
    invoice_date: str | None = Field(description="Invoice date in YYYY-MM-DD format")
    taxable_value: float | None = Field(description="Total taxable value")
    gst_amount: float | None = Field(description="Total GST amount (IGST + CGST + SGST)")
    total_amount: float | None = Field(description="Total invoice amount including tax")
    overall_confidence: float = Field(description="Overall confidence score between 0.0 and 1.0")
    confidence_per_field: dict[str, float] = Field(description="Confidence score between 0.0 and 1.0 for each extracted field (supplier_name, supplier_gstin, invoice_number, invoice_date, taxable_value, gst_amount, total_amount)")


class GeminiExtractionAdapter(ExtractionAdapter):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")
        self.client = genai.Client(api_key=api_key)

    async def extract(self, file_bytes: bytes, mime_type: str) -> ExtractedInvoiceData:
        # Prepare the file for the API
        document = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type
        )
        
        prompt = """
        Extract the following information from the provided invoice image.
        If a field is not present or cannot be read, set its value to null.
        Also provide an overall confidence score (0.0 to 1.0) and a confidence score for each field.
        Be especially careful with the GSTIN; if it's blurry, assign a low confidence score.
        """

        # Since extract is async, but self.client.models.generate_content is sync by default,
        # we can use generate_content since it's an IO bound operation that typically in this backend
        # is running in an async context, ideally we would use async client but genai has aios.
        # I'll use aio.generate_content to make it non-blocking.
        response = await self.client.aio.models.generate_content(
            model='gemini-2.5-pro',
            contents=[document, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=InvoiceSchema,
                temperature=0.0
            ),
        )

        try:
            data_dict = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback if the model doesn't return pure JSON for some reason
            data_dict = {}

        return ExtractedInvoiceData(
            supplier_name=data_dict.get("supplier_name"),
            supplier_gstin=data_dict.get("supplier_gstin"),
            invoice_number=data_dict.get("invoice_number"),
            invoice_date=data_dict.get("invoice_date"),
            taxable_value=data_dict.get("taxable_value"),
            gst_amount=data_dict.get("gst_amount"),
            total_amount=data_dict.get("total_amount"),
            overall_confidence=data_dict.get("overall_confidence", 0.0),
            confidence_per_field=data_dict.get("confidence_per_field", {}),
            raw_provider_response=response.text
        )
