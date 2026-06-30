"""
Background scheduling: periodic GSTR-2A/2B sync (PRD §3.3 trigger: "a
scheduled GSTR-2A/2B sync"), weekly digest trigger (§3.4), and periodic
risk-score recomputation (Phase 3, §8.3).

Kept deliberately simple (APScheduler in-process) for an MVP; a real
deployment would move this to a managed cron/worker queue once volume
justifies it.
"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.gsp.factory import get_gsp_adapter
from app.models.business import Business
from app.services.gst_sync import GSTSyncService
from app.services.risk_scoring import RiskScoringService

logger = logging.getLogger("gisto.scheduler")


def _current_and_recent_periods(lookback: int = 3) -> list[str]:
    periods = []
    today = datetime.utcnow()
    year, month = today.year, today.month
    for _ in range(lookback):
        periods.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return periods


async def run_gst_sync_job():
    db: Session = SessionLocal()
    try:
        gsp = get_gsp_adapter()
        service = GSTSyncService(db, gsp)
        businesses = db.query(Business).filter_by(onboarding_complete=True).all()
        for business in businesses:
            for period in _current_and_recent_periods():
                try:
                    await service.sync_business_period(business, period)
                except Exception:
                    logger.exception("GST sync failed for business %s period %s", business.business_id, period)
    finally:
        db.close()


def run_risk_scoring_job():
    db: Session = SessionLocal()
    try:
        RiskScoringService(db).recompute_all()
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    # Daily sync sweep — real cadence would be tuned to the GSP's own data
    # refresh cycle once a vendor is selected (PRD §7.2).
    scheduler.add_job(run_gst_sync_job, "interval", hours=24, id="gst_sync")
    scheduler.add_job(run_risk_scoring_job, "interval", hours=24, id="risk_scoring")
    scheduler.start()
    return scheduler
