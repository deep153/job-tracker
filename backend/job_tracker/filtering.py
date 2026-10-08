import sqlite3
from collections import Counter

from job_tracker.board_sync import stored_posting
from job_tracker.filters import Rule, check
from job_tracker.search_settings import read_search


def refilter_jobs(conn: sqlite3.Connection, job_ids: list[int] | None = None) -> Counter[Rule]:
    """Re-check stored jobs (all open ones if `job_ids` is None) against the saved search settings.

    Records each job's verdict and returns how many were rejected by each rule.
    """
    rejected: Counter[Rule] = Counter()
    if job_ids == []:
        return rejected
    settings = read_search(conn)
    if job_ids is None:
        rows = conn.execute("SELECT * FROM jobs WHERE closed = 0").fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM jobs WHERE id IN ({','.join('?' * len(job_ids))})", job_ids).fetchall()
    verdicts: list[tuple[str | None, str | None, int]] = []
    for row in rows:
        rejection = check(stored_posting(row), settings)
        if rejection is None:
            verdicts.append((None, None, row["id"]))
        else:
            rejected[rejection.rule] += 1
            verdicts.append((rejection.rule, rejection.reason, row["id"]))
    conn.executemany("UPDATE jobs SET rejected_rule = ?, rejected_reason = ? WHERE id = ?", verdicts)
    return rejected
