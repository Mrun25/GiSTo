"""
GSP (GST Suvidha Provider) adapter interface — PRD §5.3.

PRD §5.3 names two distinct mechanisms a real GSP must support:
  1. GSTIN validation / active-status check (low-friction, used at
     onboarding and per-invoice).
  2. GSTR-2A/2B fetch, via the *business owner's own* authenticated GST
     session (OTP-based consent) — never the supplier's.

PRD §5.3's open item: vendor not yet selected (WhiteBooks vs GSTHero,
evaluated on per-call cost, sandbox quality, and OTP/consent UX). This
interface is the seam: every concrete adapter (mock now, a real vendor
later) implements exactly this contract, so picking a vendor is a config
change (GSP_PROVIDER env var) — see app/gsp/factory.py — not a rewrite of
the matching/alerting logic in app/services/.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class GSTINValidationResult:
    gstin: str
    is_valid: bool
    is_active: bool
    legal_name: str | None
    state: str | None


@dataclass
class FilingRecord:
    """One supplier's filing status for one return period, as seen in the
    business owner's GSTR-2A/2B (PRD §5.3, §6.4 filing_history shape)."""
    supplier_gstin: str
    period: str  # "YYYY-MM"
    filed: bool
    filed_on_time: bool
    filed_date: date | None
    taxable_value_reported: float | None  # what the supplier reported, for reconciliation


class GSPAdapter(ABC):
    """Every GSP integration (mock, WhiteBooks, GSTHero, ...) implements this."""

    @abstractmethod
    async def validate_gstin(self, gstin: str) -> GSTINValidationResult:
        """GSTIN validation / active-status check (PRD §5.3, used at
        onboarding §3.1 and per-invoice §3.2)."""
        ...

    @abstractmethod
    async def start_otp_session(self, gstin: str) -> str:
        """Kick off the GSP-hosted GST OTP login (PRD §3.1) for a business's
        own GST session. Returns an authorization URL the bot sends to the
        owner. GiSTo never sees the owner's GST portal password."""
        ...

    @abstractmethod
    async def complete_otp_session(self, gstin: str, otp_reference: str) -> tuple[str, date]:
        """Finalize OTP auth. Returns (session_token, token_expiry)."""
        ...

    @abstractmethod
    async def fetch_2a_2b(
        self, business_gstin: str, session_token: str, period: str
    ) -> list[FilingRecord]:
        """Pull GSTR-2A/2B for one period using the owner's own authenticated
        session (PRD §5.3). This is how non-filing is detected without
        needing the supplier's own consent or login."""
        ...
