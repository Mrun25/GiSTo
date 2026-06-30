"""
WhatsApp channel — Phase 4 (PRD §8.4), exploratory, not committed.

PRD §5.2 is explicit about why this exists as an empty shell rather than
nothing: "Core logic (extraction, GST matching, alerting) should stay
decoupled from the messaging layer so a future WhatsApp surface does not
require rebuilding the underlying system." This package is the proof of
that decoupling — it talks to the exact same FastAPI backend the
Telegram bot talks to (see bot/app/api_client.py), through the same
HTTP contract. None of app/services/ or app/models/ in the backend
changes to support this.

This is intentionally NOT a working WhatsApp integration: doing that for
real requires a WhatsApp Business API provider (e.g. Meta Cloud API,
Twilio, Gupshup), business-message template approval, and a verified
business — all real-world registration steps outside this codebase's
control (PRD §5.2 names this explicitly as the reason Telegram was
chosen first). What's here is the integration *shape*: the same
conversation flows as the Telegram bot (onboarding, invoice submission,
alerts, digest), reimplemented against a generic "send/receive message"
interface so swapping in a real WhatsApp provider SDK later is additive.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IncomingMessage:
    sender_id: str  # WhatsApp phone number / wa_id
    text: str | None
    media_bytes: bytes | None
    media_mime_type: str | None


class WhatsAppProvider(ABC):
    """Implement this against a real provider (Meta Cloud API, Twilio,
    Gupshup, etc.) once Phase 4 is greenlit. See module docstring."""

    @abstractmethod
    async def send_text(self, to: str, text: str) -> None: ...

    @abstractmethod
    async def send_buttons(self, to: str, text: str, buttons: list[tuple[str, str]]) -> None:
        """buttons: list of (label, callback_id) — WhatsApp's interactive
        message buttons are the rough equivalent of Telegram's inline
        keyboards used throughout bot/app/handlers/."""
        ...


class StubWhatsAppProvider(WhatsAppProvider):
    """No-op provider so this package is importable/testable without any
    real WhatsApp credentials. Logs what *would* be sent."""

    def __init__(self):
        self.sent: list[dict] = []

    async def send_text(self, to: str, text: str) -> None:
        self.sent.append({"to": to, "type": "text", "text": text})

    async def send_buttons(self, to: str, text: str, buttons: list[tuple[str, str]]) -> None:
        self.sent.append({"to": to, "type": "buttons", "text": text, "buttons": buttons})
