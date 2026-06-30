"""
GiSTo Telegram bot — Phase 1 (PRD §3, §5.1, §5.2).

Wires together onboarding (§3.1), invoice submission (§3.2), alert
actions (§3.3), digest (§3.4), and CA invite capture (§3.5). Talks to
the FastAPI backend exclusively via app.api_client — no direct DB access,
so the bot stays a thin presentation layer over shared backend logic
(this is also what makes a future WhatsApp surface, PRD §5.2/§8.4, a
matter of writing a new bot/ -equivalent rather than touching the core).
"""
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from telegram.ext import Application, MessageHandler, filters

from app.handlers.onboarding import build_onboarding_handler
from app.handlers.invoice import (
    handle_invoice_file, on_confirm_or_correct, on_field_selected, on_new_value,
    get_invoice_message_filter, CONFIRM_OR_CORRECT, CORRECTING_FIELD, NEW_VALUE,
)
from app.handlers.alerts import build_alert_handlers
from app.handlers.digest import build_digest_handler
from app.services.notifier import poll_and_notify_new_alerts, send_weekly_digests
from telegram.ext import ConversationHandler, CallbackQueryHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("gisto.bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALERT_SWEEP_INTERVAL_SECONDS = int(os.environ.get("ALERT_SWEEP_INTERVAL_SECONDS", 3600))  # hourly
DIGEST_INTERVAL_SECONDS = int(os.environ.get("DIGEST_INTERVAL_SECONDS", 7 * 24 * 3600))  # weekly


def build_invoice_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(get_invoice_message_filter(), handle_invoice_file)],
        states={
            CONFIRM_OR_CORRECT: [CallbackQueryHandler(on_confirm_or_correct, pattern=r"^(confirm|correct)$")],
            CORRECTING_FIELD: [CallbackQueryHandler(on_field_selected, pattern=r"^field:")],
            NEW_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_new_value)],
        },
        fallbacks=[],
        # This conversation mixes text messages and callback-query button
        # presses across states, so per-message tracking (which assumes
        # every state is reached by a callback query) doesn't apply here.
        per_message=False,
    )


def main() -> None:
    token = BOT_TOKEN
    is_test = False
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Using dummy token for testing wiring.")
        token = "dummy_token_for_testing"
        is_test = True

    app = Application.builder().token(token).build()

    app.add_handler(build_onboarding_handler())
    app.add_handler(build_invoice_handler())
    for handler in build_alert_handlers():
        app.add_handler(handler)
    app.add_handler(build_digest_handler())

    from app.handlers.chat import build_chat_handler
    app.add_handler(build_chat_handler())

    # Proactive side of PRD §3.3 (push new alerts) and §3.4 (weekly digest).
    # JobQueue requires the `python-telegram-bot[job-queue]` extra (APScheduler);
    # see bot/requirements.txt.
    if app.job_queue is not None:
        app.job_queue.run_repeating(
            lambda ctx: poll_and_notify_new_alerts(ctx.application),
            interval=ALERT_SWEEP_INTERVAL_SECONDS, first=30, name="alert_sweep",
        )
        app.job_queue.run_repeating(
            lambda ctx: send_weekly_digests(ctx.application),
            interval=DIGEST_INTERVAL_SECONDS, first=60, name="weekly_digest",
        )
    else:
        logger.warning("JobQueue unavailable — install python-telegram-bot[job-queue] for proactive alerts/digests.")

    if is_test:
        logger.info("GiSTo bot wiring test complete. Skipping polling.")
        return

    logger.info("GiSTo bot starting (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
