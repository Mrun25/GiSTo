"""
Factory that picks the GSP adapter based on settings.gsp_provider.
This is the single place a real vendor integration gets wired in once
selected (PRD §5.3, §7.2 open item).
"""
from functools import lru_cache

from app.core.config import get_settings
from app.gsp.base import GSPAdapter
from app.gsp.mock_gsp import MockGSPAdapter


@lru_cache
def get_gsp_adapter() -> GSPAdapter:
    settings = get_settings()
    if settings.gsp_provider == "mock":
        return MockGSPAdapter()
    # Placeholder seams for when a vendor is selected:
    # if settings.gsp_provider == "whitebooks":
    #     from app.gsp.whitebooks_gsp import WhiteBooksGSPAdapter
    #     return WhiteBooksGSPAdapter(api_key=settings.gsp_api_key, base_url=settings.gsp_base_url)
    # if settings.gsp_provider == "gsthero":
    #     from app.gsp.gsthero_gsp import GSTHeroGSPAdapter
    #     return GSTHeroGSPAdapter(api_key=settings.gsp_api_key, base_url=settings.gsp_base_url)
    raise ValueError(f"Unknown GSP provider: {settings.gsp_provider}")
