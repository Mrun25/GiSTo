import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from google import genai

from app.core.db import get_db
from app.core.config import get_settings
from app.models.business import Business
from app.models.invoice import Invoice
from app.models.alert import Alert


router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    telegram_id: str
    query: str

class ChatResponse(BaseModel):
    reply: str

@router.post("/", response_model=ChatResponse)
async def handle_chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Fetch business context
    business = db.scalar(select(Business).where(Business.owner_telegram_id == request.telegram_id))
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    # Get recent invoices (e.g., last 10)
    invoices = db.scalars(
        select(Invoice)
        .where(Invoice.business_id == business.business_id)
        .order_by(Invoice.invoice_date.desc())
        .limit(10)
    ).all()
    
    # Get active alerts
    alerts = db.scalars(
        select(Alert)
        .where(Alert.business_id == business.business_id)
        .where(Alert.status != "resolved")
    ).all()
    
    # Prepare context string
    context_str = f"Business Name: {business.name}\nGSTIN: {business.gstin}\n\nRecent Invoices:\n"
    for inv in invoices:
        context_str += f"- {inv.invoice_number} from {inv.supplier.name if inv.supplier else 'Unknown'} on {inv.invoice_date}: {inv.total_amount}\n"
        
    context_str += "\nOpen Alerts:\n"
    for alert in alerts:
        context_str += f"- {alert.alert_type}: {alert.risk_reason}\n"
        
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini API key is not configured")
        
    client = genai.Client(api_key=settings.gemini_api_key)
    
    prompt = f"""
You are the intelligent assistant for GiSTo (a GST tracking app for small businesses).
The user is the business owner. Answer their question concisely based on the context below.
If the context doesn't have the answer, politely say you don't know or don't have that information.

Context:
{context_str}

User Question:
{request.query}
"""

    response = await client.aio.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    
    return ChatResponse(reply=response.text)
