import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.alert import Alert
from app.models.supplier import Supplier
from app.schemas.alert import AlertOut, AlertActionRequest, ReminderDraftOut, DigestOut
from app.services.alert_service import AlertService

router = APIRouter(tags=["alerts"])


@router.get("/alerts/by-business/{business_id}", response_model=list[AlertOut])
def list_alerts(business_id: uuid.UUID, open_only: bool = True, db: Session = Depends(get_db)):
    query = db.query(Alert).filter_by(business_id=business_id)
    if open_only:
        query = query.filter(Alert.status != "resolved")
    alerts = query.order_by(Alert.amount_at_risk.desc()).all()
    out = []
    for a in alerts:
        supplier = db.get(Supplier, a.supplier_gstin)
        out.append(AlertOut(
            alert_id=a.alert_id, business_id=a.business_id, supplier_gstin=a.supplier_gstin,
            supplier_name=supplier.legal_name if supplier else None,
            period=a.period, amount_at_risk=float(a.amount_at_risk), status=a.status,
            notes=a.notes, created_at=a.created_at,
        ))
    return out


@router.post("/alerts/{alert_id}/action", response_model=ReminderDraftOut | None)
def act_on_alert(alert_id: uuid.UUID, payload: AlertActionRequest, db: Session = Depends(get_db)):
    """PRD §3.3: send_reminder (drafted message returned for owner approval —
    never sent automatically), snooze, or mark_resolved."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    service = AlertService(db)

    if payload.action == "send_reminder":
        return service.draft_reminder(alert)
    elif payload.action == "confirm_reminder_sent":
        service.mark_reminder_sent(alert)
        return None
    elif payload.action == "snooze":
        service.snooze(alert, payload.snooze_days or 7)
        return None
    elif payload.action == "mark_resolved":
        service.mark_resolved(alert, payload.note)
        return None
    raise HTTPException(400, f"Unknown action: {payload.action}")


@router.get("/digest/{business_id}", response_model=DigestOut)
def get_digest(business_id: uuid.UUID, period_label: str = "this period", db: Session = Depends(get_db)):
    """PRD §3.4."""
    service = AlertService(db)
    return service.build_digest(business_id, period_label)
