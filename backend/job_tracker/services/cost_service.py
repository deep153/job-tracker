from job_tracker.database import Database
from job_tracker.models.ai import CostSummary

RECENT_RUNS = 10


class CostService:
    """What the AI calls have cost, estimated from their token counts."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def summary(self) -> CostSummary:
        with self._db.transaction() as uow:
            return CostSummary(uow.scores.usage_by_kind(), uow.runs.recent_with_ai_cost(RECENT_RUNS))
