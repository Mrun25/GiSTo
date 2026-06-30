"""
/start onboarding flow — PRD §3.1.

Steps:
  1. /start -> ask for GSTIN
  2. validate via GSP, show back name/state, ask owner to confirm
  3. explain GST sync requirement, send OTP authorization link
  4. owner completes OTP elsewhere; bot polls/accepts a reference code
     to "complete" it (mocked: any text after the link is treated as the
     OTP reference, since there's no real GSP portal in this MVP)
  5. ask if owner works with a CA; capture contact if yes
  6. confirm setup complete, explain core loop
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from app.api_client import GiStoAPIClient

GSTIN, CONFIRM_BUSINESS, AWAIT_OTP, ASK_CA, CA_CONTACT = range(5)

api = GiStoAPIClient()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = str(update.effective_user.id)
    existing = await api.get_business_by_telegram(telegram_id)
    if existing and existing.get("onboarding_complete"):
        await update.message.reply_text(
            f"Welcome back, {existing['name']}! Just send me any invoice — photo, PDF, or screenshot — "
            "and I'll take it from there. Send /summary anytime for your digest."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Welcome to GiSTo! 👋\n\n"
        "I'll help you track invoices and warn you in real time if a supplier hasn't filed their GST — "
        "so you don't silently lose Input Tax Credit.\n\n"
        "First, what's your business's GSTIN?"
    )
    return GSTIN


async def receive_gstin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gstin = update.message.text.strip().upper()
    validation = await api.validate_gstin(gstin)
    if not validation["is_valid"]:
        await update.message.reply_text("That doesn't look like a valid GSTIN. Could you double-check and resend it?")
        return GSTIN

    context.user_data["gstin"] = gstin
    context.user_data["validation"] = validation
    status_note = "" if validation["is_active"] else "\n⚠️ Note: this GSTIN currently shows as cancelled/inactive."
    await update.message.reply_text(
        f"Found it:\n*{validation['legal_name']}*\nState: {validation['state']}{status_note}\n\n"
        "Is this correct? (yes/no)",
        parse_mode="Markdown",
    )
    return CONFIRM_BUSINESS


async def confirm_business(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text not in ("yes", "y"):
        await update.message.reply_text("No problem — please resend the correct GSTIN.")
        return GSTIN

    telegram_id = str(update.effective_user.id)
    business = await api.create_business(telegram_id, context.user_data["gstin"])
    context.user_data["business_id"] = business["business_id"]

    otp = await api.start_otp(business["business_id"])
    await update.message.reply_text(
        "Great. To check whether your suppliers have filed their GST, I need to sync with the GST system "
        "using a one-time secure login — I never see your GST portal password.\n\n"
        f"Open this link to authorize: {otp['authorization_url']}\n\n"
        "Once you've completed the OTP step there, reply here with the confirmation code it gives you "
        "(for this demo, you can just type anything, e.g. `done`)."
    )
    return AWAIT_OTP


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    otp_reference = update.message.text.strip()
    business_id = context.user_data["business_id"]
    await api.complete_otp(business_id, otp_reference)
    await update.message.reply_text(
        "✅ Authorization successful. I'll now keep an eye on your suppliers' filing status automatically.\n\n"
        "Do you work with a CA or accountant? (yes/no)"
    )
    return ASK_CA


async def ask_ca_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    if text in ("yes", "y"):
        await update.message.reply_text("Great — what's their name and phone number or email? (e.g. \"Mrunmayee, mrunmayee@example.com\")")
        return CA_CONTACT
    return await finish_onboarding(update, context)


async def receive_ca_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if "," in text:
        name, contact = (p.strip() for p in text.split(",", 1))
    else:
        name, contact = text, text
    business_id = context.user_data["business_id"]
    await api.create_ca_invite(business_id, name, contact)
    await update.message.reply_text(f"Got it — I've sent an invite to {name}. They'll get dashboard access once available.")
    return await finish_onboarding(update, context)


async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🎉 You're all set up!\n\n"
        "Just send me any invoice — photo, PDF, or screenshot — and I'll extract the details, "
        "track it, and warn you if a supplier doesn't file. Try sending one now, or type /summary "
        "to see your digest anytime."
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Setup cancelled. Send /start anytime to begin again.")
    return ConversationHandler.END


def build_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GSTIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_gstin)],
            CONFIRM_BUSINESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_business)],
            AWAIT_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)],
            ASK_CA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ca_response)],
            CA_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ca_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
