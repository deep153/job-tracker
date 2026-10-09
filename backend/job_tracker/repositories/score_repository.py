import json
import sqlite3

from job_tracker.models.ai import UsageByKind
from job_tracker.models.job import FitResult


class ScoreRepository:
    """Fit scores, and the AI usage behind them."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, job_id: int, content_hash: str, resume_version: int, fit: FitResult, scored_at: str) -> None:
        """Replaces any earlier score for this job and resume version, so the newest score has the highest id."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO scores (job_id, resume_version, content_hash, score, reasons, matched_keywords,
                missing_keywords, model, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                resume_version,
                content_hash,
                fit.score,
                json.dumps(fit.reasons),
                json.dumps(fit.matched_keywords),
                json.dumps(fit.missing_keywords),
                fit.model,
                scored_at,
            ),
        )

    def record_usage(
        self,
        kind: str,
        run_id: int | None,
        job_id: int | None,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        created_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO ai_usage (kind, run_id, job_id, model, input_tokens, output_tokens, cost_usd, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (kind, run_id, job_id, model, input_tokens, output_tokens, cost_usd, created_at),
        )

    def usage_by_kind(self) -> list[UsageByKind]:
        rows = self._conn.execute(
            """
            SELECT kind, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd, SUM(input_tokens) AS input_tokens,
                SUM(output_tokens) AS output_tokens
            FROM ai_usage GROUP BY kind ORDER BY kind
            """
        ).fetchall()
        return [
            UsageByKind(row["kind"], row["calls"], row["cost_usd"], row["input_tokens"], row["output_tokens"])
            for row in rows
        ]
