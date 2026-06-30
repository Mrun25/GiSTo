"""
Demonstrates that the same GiSTo backend contract (bot/app/api_client.py's
shape) drives a WhatsApp conversation the same way it drives Telegram —
this is the proof of PRD §5.2's "decoupled from the messaging layer"
requirement, not a production WhatsApp integration (see provider.py
docstring for what's still needed before Phase 4 is real).

Run with: python -m whatsapp.demo_flow   (from the gisto/ project root,
after `pip install httpx`, with the backend running and reachable at
BACKEND_BASE_URL)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))

from app.api_client import GiStoAPIClient  # reuses the exact same client the Telegram bot uses
from whatsapp.provider import StubWhatsAppProvider


async def simulate_onboarding(wa_number: str):
    api = GiStoAPIClient()
    provider = StubWhatsAppProvider()

    await provider.send_text(wa_number, "Welcome to GiSTo! What's your business's GSTIN?")
    validation = await api.validate_gstin("27AAACR1234A1ZP")
    await provider.send_text(
        wa_number,
        f"Found it: {validation['legal_name']}, {validation['state']}. Is this correct?",
    )
    business = await api.create_business(wa_number, "27AAACR1234A1ZP")
    otp = await api.start_otp(business["business_id"])
    await provider.send_text(wa_number, f"Authorize here: {otp['authorization_url']}")
    await api.complete_otp(business["business_id"], "demo-otp-ref")
    await provider.send_buttons(
        wa_number, "All set! Send an invoice anytime.",
        buttons=[("View summary", "summary"), ("View alerts", "alerts")],
    )

    print("Messages the WhatsApp provider would have sent:")
    for m in provider.sent:
        print(" -", m)


if __name__ == "__main__":
    asyncio.run(simulate_onboarding("whatsapp:+919876543210"))
