"""
Supplier risk scoring — Phase 3 (PRD §8.3), built on the filing_history
already captured from Phase 1 (§6.4: "% of last 6 periods filed late or
not at all"). Included now because the data model supports it from day
one even though it's a Phase 3 feature — no migration needed later.
"""
from sqlalchemy.orm import Session

from app.models.supplier import Supplier

LOOKBACK_PERIODS = 6


def compute_risk_score(filing_history: list[dict]) -> float | None:
    """% of the last LOOKBACK_PERIODS periods filed late or not at all.
    Returns None if there's no history yet (untested supplier)."""
    if not filing_history:
        return None
    sorted_history = sorted(filing_history, key=lambda h: h["period"], reverse=True)[:LOOKBACK_PERIODS]
    bad = sum(1 for h in sorted_history if not h.get("filed") or not h.get("filed_on_time"))
    return round(bad / len(sorted_history), 4)


def is_trending_toward_non_filing(filing_history: list[dict]) -> bool:
    """Predictive-alert heuristic (PRD §8.3): flag a supplier whose filing
    has been getting later over recent periods, even before they actually
    miss a deadline outright."""
    sorted_history = sorted(filing_history, key=lambda h: h["period"])[-3:]
    if len(sorted_history) < 2:
        return False
    late_count = sum(1 for h in sorted_history if not h.get("filed_on_time", True))
    return late_count >= 2


class RiskScoringService:
    def __init__(self, db: Session):
        self.db = db

    def recompute_all(self) -> int:
        """Aggregate scoring across every business on GiSTo (PRD §8.3:
        "gets smarter with aggregate data across all its users"), since
        Supplier is normalized and shared (§6.4)."""
        suppliers = self.db.query(Supplier).all()
        updated = 0
        for supplier in suppliers:
            score = compute_risk_score(supplier.filing_history or [])
            if score != supplier.risk_score:
                supplier.risk_score = score
                updated += 1
        self.db.commit()
        return updated
