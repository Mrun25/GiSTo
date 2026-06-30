"""
Proactive push notifications — the half of PRD §3.3/§3.4 that isn't
owner-initiated: the bot reaching out *to* the owner when a scheduled
sync finds a new risk, or on the weekly digest cadence.

This polls the backend for newly-created open alerts rather than the
backend pushing to the bot, to keep the backend transport-agnostic
(PRD §5.2: "core logic should stay decoupled from the messaging layer").
A production version would likely use a backend-side webhook/queue
instead of polling once volume justifies it.
"""
import asyncio
import logging

from telegram.ext import Application

from app.api_client import GiStoAPIClient
from app.handlers.alerts import render_alert_card
from app.handlers.digest import render_digest

logger = logging.getLogger("gisto.bot.notifier")

api = GiStoAPIClient()

_notified_alert_ids: set[str] = set()


async def poll_and_notify_new_alerts(app: Application) -> None:
    """Called periodically; for each onboarded business, checks for open
    alerts not yet pushed to the owner and sends them proactively."""
    try:
        businesses = await api.list_onboarded_businesses()
    except Exception:
        logger.exception("Failed to list onboarded businesses for notifier sweep")
        return

    for business in businesses:
        try:
            alerts = await api.list_alerts(business["business_id"], open_only=True)
            for alert in alerts:
                await send_alert_to_owner(app, business["owner_telegram_id"], alert)
        except Exception:
            logger.exception("Failed to notify business %s", business.get("business_id"))


async def send_weekly_digests(app: Application) -> None:
    """Weekly automatic digest (PRD §3.4 trigger)."""
    try:
        businesses = await api.list_onboarded_businesses()
    except Exception:
        logger.exception("Failed to list onboarded businesses for digest sweep")
        return

    for business in businesses:
        try:
            await send_weekly_digest_to_owner(app, business["owner_telegram_id"], business["business_id"])
        except Exception:
            logger.exception("Failed to send digest to business %s", business.get("business_id"))


async def send_alert_to_owner(app: Application, telegram_id: str, alert: dict) -> None:
    if alert["alert_id"] in _notified_alert_ids:
        return
    text, markup = render_alert_card(alert)
    await app.bot.send_message(chat_id=telegram_id, text=text, parse_mode="Markdown", reply_markup=markup)
    _notified_alert_ids.add(alert["alert_id"])


async def send_weekly_digest_to_owner(app: Application, telegram_id: str, business_id: str) -> None:
    digest = await api.get_digest(business_id, period_label="this week")
    await app.bot.send_message(chat_id=telegram_id, text=render_digest(digest), parse_mode="Markdown")
