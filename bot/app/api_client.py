"""
Thin async HTTP client the bot uses to talk to the GiSTo backend API.
Keeps all backend-shape knowledge in one place so handlers stay focused
on conversation flow, not request plumbing.
"""
import os

import httpx

BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://backend:8000")


class GiStoAPIClient:
    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    # --- Onboarding (PRD §3.1) ---
    async def validate_gstin(self, gstin: str) -> dict:
        async with await self._client() as c:
            r = await c.post("/businesses/validate-gstin", json={"gstin": gstin})
            r.raise_for_status()
            return r.json()

    async def create_business(self, owner_telegram_id: str, gstin: str) -> dict:
        async with await self._client() as c:
            r = await c.post("/businesses", params={"owner_telegram_id": owner_telegram_id, "gstin": gstin})
            r.raise_for_status()
            return r.json()

    async def get_business_by_telegram(self, telegram_id: str) -> dict | None:
        async with await self._client() as c:
            r = await c.get(f"/businesses/by-telegram/{telegram_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def start_otp(self, business_id: str) -> dict:
        async with await self._client() as c:
            r = await c.post(f"/businesses/{business_id}/otp/start")
            r.raise_for_status()
            return r.json()

    async def complete_otp(self, business_id: str, otp_reference: str) -> dict:
        async with await self._client() as c:
            r = await c.post("/businesses/otp/complete", json={"business_id": business_id, "otp_reference": otp_reference})
            r.raise_for_status()
            return r.json()

    # --- Invoice submission (PRD §3.2) ---
    async def extract_invoice(self, file_bytes: bytes, filename: str, mime_type: str) -> dict:
        async with await self._client() as c:
            files = {"file": (filename, file_bytes, mime_type)}
            r = await c.post("/invoices/extract", files=files)
            r.raise_for_status()
            return r.json()

    async def confirm_invoice(self, payload: dict) -> dict:
        async with await self._client() as c:
            r = await c.post("/invoices/confirm", json=payload)
            r.raise_for_status()
            return r.json()

    # --- Alerts (PRD §3.3) ---
    async def list_alerts(self, business_id: str, open_only: bool = True) -> list[dict]:
        async with await self._client() as c:
            r = await c.get(f"/alerts/by-business/{business_id}", params={"open_only": open_only})
            r.raise_for_status()
            return r.json()

    async def alert_action(self, alert_id: str, action: str, snooze_days: int | None = None, note: str | None = None) -> dict | None:
        async with await self._client() as c:
            r = await c.post(f"/alerts/{alert_id}/action", json={"action": action, "snooze_days": snooze_days, "note": note})
            r.raise_for_status()
            return r.json() if r.content else None

    # --- Digest (PRD §3.4) ---
    async def get_digest(self, business_id: str, period_label: str = "this period") -> dict:
        async with await self._client() as c:
            r = await c.get(f"/digest/{business_id}", params={"period_label": period_label})
            r.raise_for_status()
            return r.json()

    # --- CA invite (PRD §3.5) ---
    async def create_ca_invite(self, business_id: str, ca_name: str, ca_contact: str) -> dict:
        async with await self._client() as c:
            r = await c.post("/ca/invite", json={"business_id": business_id, "ca_name": ca_name, "ca_contact": ca_contact})
            r.raise_for_status()
            return r.json()

    # --- Internal: used by the notifier sweep ---
    async def list_onboarded_businesses(self) -> list[dict]:
        async with await self._client() as c:
            r = await c.get("/businesses")
            r.raise_for_status()
            return r.json()

    # --- Chat (Intelligent Assistant) ---
    async def chat(self, telegram_id: str, query: str) -> dict:
        async with await self._client() as c:
            r = await c.post("/chat/", json={"telegram_id": telegram_id, "query": query})
            r.raise_for_status()
            return r.json()
