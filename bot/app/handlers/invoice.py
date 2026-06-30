"""
Invoice submission — PRD §3.2 (core loop).

Owner sends a photo/PDF/document -> bot extracts -> shows confirmation
card -> owner confirms or corrects a field -> stored.

Design rule (§3.2): any field with low confidence — especially GSTIN —
is always shown back to the owner for confirmation, never auto-accepted.
We surface this by listing flagged fields explicitly in the card and
requiring an explicit "confirm" before storing.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from app.api_client import GiStoAPIClient

CONFIRM_OR_CORRECT, CORRECTING_FIELD, NEW_VALUE = range(3)

api = GiStoAPIClient()

FIELD_LABELS = {
    "supplier_gstin": "Supplier GSTIN",
    "invoice_number": "Invoice number",
    "invoice_date": "Invoice date",
    "taxable_value": "Taxable value",
    "gst_amount": "GST amount",
}


def _format_card(extracted: dict) -> str:
    review_fields = set(extracted.get("fields_requiring_review", []))
    lines = ["📄 *Here's what I read from the invoice:*\n"]
    rows = [
        ("supplier_name", "Supplier", extracted.get("supplier_name")),
        ("supplier_gstin", "GSTIN", extracted.get("supplier_gstin")),
        ("invoice_number", "Invoice #", extracted.get("invoice_number")),
        ("invoice_date", "Date", extracted.get("invoice_date")),
        ("taxable_value", "Taxable value", extracted.get("taxable_value")),
        ("gst_amount", "GST amount", extracted.get("gst_amount")),
        ("total_amount", "Total", extracted.get("total_amount")),
    ]
    for key, label, value in rows:
        flag = " ⚠️ *please double-check*" if key in review_fields else ""
        lines.append(f"• {label}: {value}{flag}")

    gstin_status = extracted.get("supplier_gstin_status")
    if gstin_status == "cancelled":
        lines.append("\n⚠️ This supplier's GSTIN currently shows as *cancelled*.")

    if review_fields:
        lines.append("\nI flagged some fields with lower confidence — please confirm they're right before I save this.")
    return "\n".join(lines)


async def handle_invoice_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message.photo:
        file = await message.photo[-1].get_file()
        filename, mime_type = "invoice.jpg", "image/jpeg"
    elif message.document:
        file = await message.document.get_file()
        filename = message.document.file_name or "invoice"
        mime_type = message.document.mime_type or "application/octet-stream"
    else:
        await message.reply_text("Please send the invoice as a photo, PDF, or document.")
        return ConversationHandler.END

    file_bytes = bytes(await file.download_as_bytearray())
    await message.reply_text("Got it — reading the invoice now...")

    extracted = await api.extract_invoice(file_bytes, filename, mime_type)
    context.user_data["pending_invoice"] = extracted
    context.user_data["source_file"] = filename

    keyboard = [[
        InlineKeyboardButton("✅ Looks right", callback_data="confirm"),
        InlineKeyboardButton("✏️ Fix a field", callback_data="correct"),
    ]]
    await message.reply_text(_format_card(extracted), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_OR_CORRECT


async def on_confirm_or_correct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm":
        return await _store_invoice(update, context)

    # correct -> ask which field
    keyboard = [[InlineKeyboardButton(label, callback_data=f"field:{key}")] for key, label in FIELD_LABELS.items()]
    await query.edit_message_text("Which field should I fix?")
    await query.message.reply_text("Pick one:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CORRECTING_FIELD


async def on_field_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    field_key = query.data.split(":", 1)[1]
    context.user_data["correcting_field"] = field_key
    await query.edit_message_text(f"Send the correct value for {FIELD_LABELS[field_key]}:")
    return NEW_VALUE


async def on_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field_key = context.user_data["correcting_field"]
    new_value = update.message.text.strip()
    context.user_data["pending_invoice"][field_key] = new_value
    # GSTIN corrections are exactly the case the design rule cares about —
    # confirm explicitly rather than silently re-trusting the new value too.
    await update.message.reply_text(f"Updated {FIELD_LABELS[field_key]} to: {new_value}")

    extracted = context.user_data["pending_invoice"]
    keyboard = [[
        InlineKeyboardButton("✅ Looks right now", callback_data="confirm"),
        InlineKeyboardButton("✏️ Fix another field", callback_data="correct"),
    ]]
    await update.message.reply_text(_format_card(extracted), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_OR_CORRECT


async def _store_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    telegram_id = str(update.effective_user.id)
    business = await api.get_business_by_telegram(telegram_id)
    if not business:
        await query.edit_message_text("I couldn't find your business — please /start onboarding first.")
        return ConversationHandler.END

    extracted = context.user_data["pending_invoice"]
    payload = {
        "business_id": business["business_id"],
        "direction": "purchase",
        "supplier_name": extracted.get("supplier_name"),
        "supplier_gstin": extracted.get("supplier_gstin"),
        "invoice_number": extracted.get("invoice_number"),
        "invoice_date": extracted.get("invoice_date"),
        "taxable_value": extracted.get("taxable_value"),
        "gst_amount": extracted.get("gst_amount"),
        "total_amount": extracted.get("total_amount"),
        "source_file": context.user_data.get("source_file"),
        "extraction_confidence": extracted.get("overall_confidence"),
    }
    invoice = await api.confirm_invoice(payload)
    await query.edit_message_text(
        f"✅ Saved invoice {invoice.get('invoice_number') or invoice['invoice_id'][:8]}. "
        "I'll let you know if this supplier doesn't file in time."
    )
    context.user_data.pop("pending_invoice", None)
    return ConversationHandler.END


def get_invoice_message_filter():
    return filters.PHOTO | filters.Document.ALL
