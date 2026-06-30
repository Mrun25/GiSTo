"""
Factory that picks the extraction adapter based on settings.extraction_provider.
"""
from functools import lru_cache

from app.core.config import get_settings
from app.extraction.base import ExtractionAdapter
from app.extraction.mock_extraction import MockExtractionAdapter


@lru_cache
def get_extraction_adapter() -> ExtractionAdapter:
    settings = get_settings()
    if settings.extraction_provider == "mock":
        return MockExtractionAdapter()
    if settings.extraction_provider == "gemini":
        from app.extraction.gemini_extraction import GeminiExtractionAdapter
        return GeminiExtractionAdapter(api_key=settings.gemini_api_key)
    if settings.extraction_provider == "mistral":
        from app.extraction.mistral_extraction import MistralExtractionAdapter
        return MistralExtractionAdapter(api_key=settings.mistral_api_key)
    raise ValueError(f"Unknown extraction provider: {settings.extraction_provider}")
