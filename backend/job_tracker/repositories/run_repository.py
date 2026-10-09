import json
import sqlite3
from collections import Counter
from dataclasses import asdict

from job_tracker.models.ai import RunCost
from job_tracker.models.job import RULES, Rule
from job_tracker.models.run import Run, RunError, RunStage, RunStatus


class RunRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def mark_running_as_interrupted(self, at: str) -> None:
        self._conn.execute("UPDATE runs SET status = 'interrupted', finished_at = ? WHERE status = 'running'", (at,))

    def any_running(self) -> bool:
        return self._conn.execute("SELECT 1 FROM runs WHERE status = 'running'").fetchone() is not None

    def create(self, started_at: str) -> int:
        run_id = self._conn.execute(
            "INSERT INTO runs (status, stage, started_at) VALUES ('running', 'discovering', ?)", (started_at,)
        ).lastrowid
        assert run_id is not None
        return run_id

    def get(self, run_id: int) -> Run | None:
        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return None if row is None else _run(row)

    def recent(self, limit: int) -> list[Run]:
        return [_run(row) for row in self._conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))]

    def recent_with_ai_cost(self, limit: int) -> list[RunCost]:
        rows = self._conn.execute(
            "SELECT * FROM runs WHERE scoring_total > 0 OR ai_cost_usd > 0 ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [RunCost(row["id"], row["started_at"], row["scored_jobs"], row["ai_cost_usd"]) for row in rows]

    def finish(self, run_id: int, status: RunStatus, finished_at: str) -> None:
        self._conn.execute("UPDATE runs SET status = ?, finished_at = ? WHERE id = ?", (status, finished_at, run_id))

    def record_discovery(self, run_id: int, queries: int, capped: bool, discovered: int) -> None:
        self._conn.execute(
            """
            UPDATE runs SET stage = 'fetching', search_queries = ?, search_queries_capped = ?, companies_discovered = ?
            WHERE id = ?
            """,
            (queries, capped, discovered, run_id),
        )

    def start_stage(self, run_id: int, stage: RunStage, total: int) -> None:
        """Move to a stage that works through `total` items (companies to fetch, or jobs to score)."""
        column = {"discovering": None, "fetching": "companies_total", "scoring": "scoring_total"}[stage]
        if column is None:
            self._conn.execute("UPDATE runs SET stage = ? WHERE id = ?", (stage, run_id))
        else:
            self._conn.execute(f"UPDATE runs SET stage = ?, {column} = ? WHERE id = ?", (stage, total, run_id))

    def record_board_fetched(self, run_id: int, new: int, updated: int, closed: int) -> None:
        self._conn.execute(
            """
            UPDATE runs SET companies_fetched = companies_fetched + 1, new_jobs = new_jobs + ?,
                updated_jobs = updated_jobs + ?, closed_jobs = closed_jobs + ?
            WHERE id = ?
            """,
            (new, updated, closed, run_id),
        )

    def record_board_failed(self, run_id: int) -> None:
        self._conn.execute("UPDATE runs SET companies_fetched = companies_fetched + 1 WHERE id = ?", (run_id,))

    def add_filtered_out(self, run_id: int, rejected: Counter[Rule]) -> None:
        if not rejected:
            return
        row = self._conn.execute("SELECT filtered_out FROM runs WHERE id = ?", (run_id,)).fetchone()
        totals = Counter(json.loads(row["filtered_out"])) + rejected
        self._conn.execute("UPDATE runs SET filtered_out = ? WHERE id = ?", (json.dumps(totals), run_id))

    def record_scored(self, run_id: int, matched: bool, cost_usd: float) -> None:
        self._conn.execute(
            """
            UPDATE runs SET scored_jobs = scored_jobs + 1, matched_jobs = matched_jobs + ?,
                ai_cost_usd = ai_cost_usd + ?
            WHERE id = ?
            """,
            (matched, cost_usd, run_id),
        )

    def append_error(self, run_id: int, error: RunError) -> None:
        errors = json.loads(self._conn.execute("SELECT errors FROM runs WHERE id = ?", (run_id,)).fetchone()[0])
        errors.append(asdict(error))
        self._conn.execute("UPDATE runs SET errors = ? WHERE id = ?", (json.dumps(errors), run_id))


def _run(row: sqlite3.Row) -> Run:
    return Run(
        id=row["id"],
        status=row["status"],
        stage=row["stage"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        search_queries=row["search_queries"],
        search_queries_capped=bool(row["search_queries_capped"]),
        companies_discovered=row["companies_discovered"],
        companies_total=row["companies_total"],
        companies_fetched=row["companies_fetched"],
        new_jobs=row["new_jobs"],
        updated_jobs=row["updated_jobs"],
        closed_jobs=row["closed_jobs"],
        filtered_out={rule: 0 for rule in RULES} | json.loads(row["filtered_out"]),
        errors=[RunError(**error) for error in json.loads(row["errors"])],
        scoring_total=row["scoring_total"],
        scored_jobs=row["scored_jobs"],
        matched_jobs=row["matched_jobs"],
        ai_cost_usd=row["ai_cost_usd"],
    )
