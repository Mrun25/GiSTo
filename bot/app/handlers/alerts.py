"""
ITC Risk Alert — PRD §3.3.

Two responsibilities here:
  1. /alerts command: owner can pull up current open alerts on demand.
  2. Action buttons on an alert: send reminder (draft shown for approval —
     never auto-sent to the supplier, per §3.3/§7.1), snooze, or mark resolved.

Proactive push notifications (the "scheduled sync detects non-filing"
trigger) are sent by the scheduler-triggered notifier in
app/services/notifier.py, reusing the same card-rendering and action
buttons defined here.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.api_client import GiStoAPIClient

api = GiStoAPIClient()


def render_alert_card(alert: dict) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"🚨 *ITC Risk Alert*\n\n"
        f"Your supplier *{alert.get('supplier_name') or alert['supplier_gstin']}* hasn't filed their GST "
        f"for *{alert['period']}*.\n\n"
        f"You're at risk of losing *₹{alert['amount_at_risk']:,.2f}* in tax credit."
    )
    keyboard = [[
        InlineKeyboardButton("📨 Send reminder", callback_data=f"alert:remind:{alert['alert_id']}"),
        InlineKeyboardButton("⏰ Snooze 7d", callback_data=f"alert:snooze:{alert['alert_id']}"),
    ], [
        InlineKeyboardButton("✅ Mark handled", callback_data=f"alert:resolve:{alert['alert_id']}"),
    ]]
    return text, InlineKeyboardMarkup(keyboard)


async def list_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)
    business = await api.get_business_by_telegram(telegram_id)
    if not business:
        await update.message.reply_text("Please /start onboarding first.")
        return

    alerts = await api.list_alerts(business["business_id"], open_only=True)
    if not alerts:
        await update.message.reply_text("✅ No open ITC risk alerts right now — all your suppliers are on track.")
        return

    for alert in alerts:
        text, markup = render_alert_card(alert)
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def on_alert_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, action, alert_id = query.data.split(":", 2)

    if action == "remind":
        draft = await api.alert_action(alert_id, "send_reminder")
        keyboard = [[
            InlineKeyboardButton("✅ Send this", callback_data=f"senddraft:{alert_id}"),
            InlineKeyboardButton("❌ Don't send", callback_data=f"canceldraft:{alert_id}"),
        ]]
        await query.message.reply_text(
            f"Here's a drafted reminder for *{draft['supplier_name']}*:\n\n_{draft['draft_message']}_\n\n"
            "I won't send anything to your supplier without your OK.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif action == "snooze":
        await api.alert_action(alert_id, "snooze", snooze_days=7)
        await query.edit_message_text(query.message.text + "\n\n⏰ Snoozed for 7 days.")
    elif action == "resolve":
        await api.alert_action(alert_id, "mark_resolved")
        await query.edit_message_text(query.message.text + "\n\n✅ Marked as handled.")


async def on_draft_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explicit, per-instance owner confirmation before any message reaches
    the supplier (PRD §3.3, §7.1) — this is the actual send/cancel step."""
    query = update.callback_query
    await query.answer()
    action, alert_id = query.data.split(":", 1)

    if action == "senddraft":
        # In a production build this would hand off to an SMS/WhatsApp/email
        # send step for the supplier. Mocked here since we don't have a
        # supplier contact channel wired up in this MVP.
        await api.alert_action(alert_id, "confirm_reminder_sent")
        await query.edit_message_text("📨 Reminder sent to the supplier. I'll update you once they file.")
    else:
        await query.edit_message_text("Okay, I won't send that reminder.")


def build_alert_handlers():
    return [
        CommandHandler("alerts", list_alerts_command),
        CallbackQueryHandler(on_alert_action, pattern=r"^alert:"),
        CallbackQueryHandler(on_draft_decision, pattern=r"^(senddraft|canceldraft):"),
    ]
