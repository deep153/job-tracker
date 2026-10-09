from collections.abc import Iterator
from pathlib import Path

import pytest

from job_tracker.database import Database
from job_tracker.repositories.job_repository import JobRepository
from job_tracker.services.board_sync import sync_board
from tests.support.builders import posting

SEEN_AT = "2026-10-02T00:00:00+00:00"


@pytest.fixture
def jobs(tmp_path: Path) -> Iterator[JobRepository]:
    db = Database(tmp_path / "test.db")
    db.initialize()
    with db.transaction() as uow:
        yield uow.jobs


def test_new_postings_are_added_and_queued_for_filtering(jobs: JobRepository) -> None:
    result = sync_board(
        jobs, "greenhouse", "acme", [posting(external_id="1"), posting(external_id="2", title="SRE")], SEEN_AT
    )

    assert (result.new, result.updated, result.closed) == (2, 0, 0)
    assert len(result.to_filter) == 2


def test_unchanged_postings_are_not_refiltered(jobs: JobRepository) -> None:
    sync_board(jobs, "greenhouse", "acme", [posting()], SEEN_AT)

    result = sync_board(jobs, "greenhouse", "acme", [posting()], SEEN_AT)

    assert (result.new, result.updated, result.closed, result.to_filter) == (0, 0, 0, [])


def test_changed_postings_are_updated_and_refiltered(jobs: JobRepository) -> None:
    first = sync_board(jobs, "greenhouse", "acme", [posting()], SEEN_AT)

    result = sync_board(jobs, "greenhouse", "acme", [posting(description="Now mostly Kafka.")], SEEN_AT)

    assert (result.new, result.updated, result.to_filter) == (0, 1, first.to_filter)


def test_postings_no_longer_listed_are_closed_and_reopen_when_back(jobs: JobRepository) -> None:
    first = sync_board(jobs, "greenhouse", "acme", [posting()], SEEN_AT)

    gone = sync_board(jobs, "greenhouse", "acme", [], SEEN_AT)
    back = sync_board(jobs, "greenhouse", "acme", [posting()], SEEN_AT)

    assert gone.closed == 1
    assert jobs.open_ids("greenhouse", "acme") == first.to_filter
    assert (back.new, back.updated, back.to_filter) == (0, 0, first.to_filter)


def test_a_repost_under_a_new_id_is_the_same_job(jobs: JobRepository) -> None:
    first = sync_board(jobs, "greenhouse", "acme", [posting(external_id="1")], SEEN_AT)

    result = sync_board(jobs, "greenhouse", "acme", [posting(external_id="2")], SEEN_AT)

    assert (result.new, result.closed) == (0, 0)
    assert jobs.open_ids("greenhouse", "acme") == first.to_filter
