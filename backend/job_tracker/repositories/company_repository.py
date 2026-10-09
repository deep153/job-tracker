import sqlite3

from job_tracker.models.company import Company, DiscoveredBoard
from job_tracker.models.platform import Platform

_WITH_OPEN_JOBS = """
    SELECT companies.*, COUNT(jobs.id) AS open_jobs
    FROM companies
    LEFT JOIN jobs ON jobs.platform = companies.platform AND jobs.board_id = companies.board_id AND jobs.closed = 0
"""


class CompanyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_discovered(self, boards: list[DiscoveredBoard], found_at: str) -> int:
        """Remember newly found boards; returns how many weren't known before."""
        added = 0
        for board in boards:
            added += self._conn.execute(
                """
                INSERT OR IGNORE INTO companies (platform, board_id, discovered_at, discovered_query)
                VALUES (?, ?, ?, ?)
                """,
                (board.platform, board.board_id, found_at, board.query),
            ).rowcount
        return added

    def all(self) -> list[Company]:
        rows = self._conn.execute(
            f"{_WITH_OPEN_JOBS} GROUP BY companies.id ORDER BY companies.blocked, companies.board_id"
        ).fetchall()
        return [_company(row) for row in rows]

    def get(self, company_id: int) -> Company | None:
        row = self._conn.execute(
            f"{_WITH_OPEN_JOBS} WHERE companies.id = ? GROUP BY companies.id", (company_id,)
        ).fetchone()
        return None if row is None else _company(row)

    def set_blocked(self, company_id: int, blocked: bool) -> bool:
        return self._conn.execute("UPDATE companies SET blocked = ? WHERE id = ?", (blocked, company_id)).rowcount > 0

    def boards_to_fetch(self, platforms: list[Platform]) -> list[tuple[Platform, str]]:
        """Boards of companies that aren't blocked, on these platforms, oldest first."""
        if not platforms:
            return []
        rows = self._conn.execute(
            f"""
            SELECT platform, board_id FROM companies
            WHERE blocked = 0 AND platform IN ({",".join("?" * len(platforms))})
            ORDER BY id
            """,
            platforms,
        ).fetchall()
        return [(row["platform"], row["board_id"]) for row in rows]

    def record_fetched(self, platform: Platform, board_id: str, fetched_at: str) -> None:
        self._conn.execute(
            "UPDATE companies SET last_fetched_at = ?, last_error = NULL WHERE platform = ? AND board_id = ?",
            (fetched_at, platform, board_id),
        )

    def record_error(self, platform: Platform, board_id: str, message: str) -> None:
        self._conn.execute(
            "UPDATE companies SET last_error = ? WHERE platform = ? AND board_id = ?", (message, platform, board_id)
        )


def _company(row: sqlite3.Row) -> Company:
    return Company(
        id=row["id"],
        platform=row["platform"],
        board_id=row["board_id"],
        discovered_at=row["discovered_at"],
        discovered_query=row["discovered_query"],
        blocked=bool(row["blocked"]),
        last_fetched_at=row["last_fetched_at"],
        last_error=row["last_error"],
        open_jobs=row["open_jobs"],
    )
