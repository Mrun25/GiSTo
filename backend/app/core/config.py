"""
Central configuration. Everything that varies between local/dev/prod
(GSP credentials, DB url, extraction provider) lives here so swapping
the mock GSP for WhiteBooks/GSTHero later is a config change, not a
code change.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Core ---
    app_name: str = "GiSTo API"
    environment: str = "local"
    database_url: str = "postgresql+psycopg2://gisto:gisto@db:5432/gisto"
    secret_key: str = "dev-secret-change-me"

    # --- GSP (GST Suvidha Provider) ---
    # "mock" runs a deterministic fake GSP so the whole product runs without
    # real credentials. Swap to "whitebooks" / "gsthero" once a vendor is
    # selected (see PRD 5.3, 7.2 - open item).
    gsp_provider: str = "mock"
    gsp_api_key: str | None = None
    gsp_base_url: str | None = None

    # --- Invoice extraction ---
    # "mock" returns canned structured data so the core loop (3.2) is
    # demoable end to end without an LLM key. Swap to "mistral" or
    # "claude" once a key is supplied - see app/extraction/README.md.
    extraction_provider: str = "mock"
    mistral_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    # --- Telegram bot ---
    telegram_bot_token: str | None = None
    backend_base_url: str = "http://backend:8000"

    # --- Risk / alerting thresholds ---
    # Days past the statutory filing window before a missing 2A/2B entry
    # is treated as an actionable non-filing risk (PRD 3.3).
    filing_grace_period_days: int = 11

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
