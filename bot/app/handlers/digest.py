"""
/summary on-demand digest — PRD §3.4. The weekly automatic version is
sent by app/services/notifier.py on the same schedule as alert checks.
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from app.api_client import GiStoAPIClient

api = GiStoAPIClient()


def render_digest(digest: dict) -> str:
    return (
        f"📊 *Summary — {digest['period_label']}*\n\n"
        f"Invoices logged: {digest['invoices_logged_purchases']} purchases, {digest['invoices_logged_sales']} sales\n"
        f"Non-compliant suppliers: {digest['suppliers_non_compliant']}\n\n"
        f"💰 ITC at risk: ₹{digest['total_itc_at_risk']:,.2f}\n"
        f"✅ ITC secured: ₹{digest['total_itc_secured']:,.2f}"
    )


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)
    business = await api.get_business_by_telegram(telegram_id)
    if not business:
        await update.message.reply_text("Please /start onboarding first.")
        return
    digest = await api.get_digest(business["business_id"])
    await update.message.reply_text(render_digest(digest), parse_mode="Markdown")


def build_digest_handler() -> CommandHandler:
    return CommandHandler("summary", summary_command)
