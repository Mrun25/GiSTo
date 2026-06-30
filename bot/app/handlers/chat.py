from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.api_client import GiStoAPIClient

api = GiStoAPIClient()

async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)
    text = update.message.text
    
    # We should send a "typing..." action so the user knows we are processing
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        response = await api.chat(telegram_id, text)
        reply = response.get("reply", "Sorry, I couldn't understand that.")
        await update.message.reply_text(reply)
    except Exception as e:
        # If it's a 404 (Business not found), we should probably ignore it or ask them to /start
        await update.message.reply_text("An error occurred or you haven't onboarded yet. Try /start if you haven't.")

def build_chat_handler() -> MessageHandler:
    return MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message)
