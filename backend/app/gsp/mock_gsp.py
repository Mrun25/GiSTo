"""
Mock GSP adapter.

Lets the entire product (onboarding -> invoice capture -> ITC alerting)
run end-to-end on a laptop with zero real credentials. Behaviour is
deterministic (hash-based on GSTIN) rather than random, so the same
supplier always produces the same demo behaviour across restarts —
useful for screenshots, tests, and a stable seed dataset.

Swap GSP_PROVIDER=whitebooks or GSP_PROVIDER=gsthero (once a vendor is
selected per PRD §5.3/§7.2) and implement the same GSPAdapter contract;
nothing in app/services/ needs to change.
"""
import hashlib
import re
from datetime import date, datetime, timedelta

from app.gsp.base import GSPAdapter, GSTINValidationResult, FilingRecord

GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$")

_STATE_CODES = {
    "27": "Maharashtra", "07": "Delhi", "29": "Karnataka", "33": "Tamil Nadu",
    "24": "Gujarat", "06": "Haryana", "09": "Uttar Pradesh", "19": "West Bengal",
}


def _stable_hash(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


class MockGSPAdapter(GSPAdapter):

    async def validate_gstin(self, gstin: str) -> GSTINValidationResult:
        gstin = gstin.strip().upper()
        is_valid = bool(GSTIN_PATTERN.match(gstin))
        if not is_valid:
            return GSTINValidationResult(gstin=gstin, is_valid=False, is_active=False, legal_name=None, state=None)

        # ~1 in 20 GSTINs deterministically come back cancelled, so the
        # "supplier GSTIN inactive" path is exercisable in demos/tests.
        is_active = _stable_hash(gstin) % 20 != 0
        state = _STATE_CODES.get(gstin[:2], "Unknown State")
        legal_name = f"Registered Entity {gstin[2:7]}"
        return GSTINValidationResult(gstin=gstin, is_valid=True, is_active=is_active, legal_name=legal_name, state=state)

    async def start_otp_session(self, gstin: str) -> str:
        # Real GSP would return a hosted OTP login URL. Mock returns a
        # clearly-fake but well-formed link for the bot to send.
        return f"https://mock-gsp.example/otp-login?gstin={gstin}&ref={_stable_hash(gstin) % 10**8}"

    async def complete_otp_session(self, gstin: str, otp_reference: str) -> tuple[str, date]:
        token = f"mock-session-{_stable_hash(gstin + otp_reference) % 10**12}"
        expiry = (datetime.utcnow() + timedelta(days=30)).date()
        return token, expiry

    async def fetch_2a_2b(
        self, business_gstin: str, session_token: str, period: str
    ) -> list[FilingRecord]:
        """
        Deterministically simulate which of a business's known suppliers
        filed for `period`. The caller (app/services/gst_sync.py) already
        knows which supplier GSTINs the business has purchased from; in a
        real GSP this method would return *all* invoices the GST system has
        matched to the business for that period, and the service layer
        diffs that against logged purchases. The mock instead exposes a
        per-supplier filed/not-filed verdict via a helper so the service
        layer can ask "did supplier X file for period Y" — see
        `supplier_filed_for_period` below, used by gst_sync.py.
        """
        return []

    def supplier_filed_for_period(self, supplier_gstin: str, period: str) -> FilingRecord:
        """
        Deterministic per-supplier-per-period filing verdict.
        ~1 in 6 supplier-periods come back as "not filed" so the ITC risk
        alert flow (PRD §3.3) has real demo material; among filed ones,
        ~1 in 4 are late.
        """
        seed = _stable_hash(f"{supplier_gstin}:{period}")
        not_filed = seed % 6 == 0
        if not_filed:
            return FilingRecord(
                supplier_gstin=supplier_gstin, period=period, filed=False,
                filed_on_time=False, filed_date=None, taxable_value_reported=None,
            )
        filed_late = seed % 4 == 0
        year, month = (int(x) for x in period.split("-"))
        statutory_due = date(year, month, 11) if month < 12 else date(year + 1, 1, 11)
        # next month-ish
        from calendar import monthrange
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        statutory_due = date(next_year, next_month, 11)
        filed_date = statutory_due + timedelta(days=6 if filed_late else -2)
        return FilingRecord(
            supplier_gstin=supplier_gstin, period=period, filed=True,
            filed_on_time=not filed_late, filed_date=filed_date, taxable_value_reported=None,
        )
