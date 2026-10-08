from fastapi.testclient import TestClient

from tests.conftest import discover_boards, run_to_completion, wait_for_run
from tests.fakes import FakeJobBoards


def test_run_fetches_greenhouse_postings_into_jobs_list(client: TestClient, boards: FakeJobBoards) -> None:
    discover_boards(client, boards, ["acme"])

    run = run_to_completion(client)
    assert run["status"] == "finished"
    assert run["started_at"] is not None
    assert run["finished_at"] is not None

    jobs = client.get("/api/jobs").json()
    by_title = {job["title"]: job for job in jobs}
    assert set(by_title) == {"Software Engineer, Backend", "Frontend Engineer", "Site Reliability Engineer"}

    backend = by_title["Software Engineer, Backend"]
    assert backend["company"] == "acme"
    assert backend["platform"] == "greenhouse"
    assert backend["external_id"] == "4012345008"
    assert backend["locations"] == ["San Francisco, CA"]
    assert backend["remote"] is None
    assert backend["posting_url"] == "https://job-boards.greenhouse.io/acme/jobs/4012345008"
    assert backend["application_url"] == "https://job-boards.greenhouse.io/acme/jobs/4012345008"
    assert backend["updated_at"] == "2026-09-30T14:02:11-04:00"
    assert "4+ years of Python" in backend["description"]
    assert "PostgreSQL & distributed systems" in backend["description"]
    assert "<" not in backend["description"]

    assert by_title["Frontend Engineer"]["remote"] is True


def test_no_jobs_before_first_run(client: TestClient) -> None:
    assert client.get("/api/jobs").json() == []


def test_second_run_records_only_the_new_posting(client: TestClient, boards: FakeJobBoards) -> None:
    discover_boards(client, boards, ["acme"])
    first = run_to_completion(client)
    assert first["new_jobs"] == 3

    boards.serve("greenhouse", "acme", "acme-later")
    second = run_to_completion(client)

    assert second["new_jobs"] == 1
    titles = {job["title"] for job in client.get("/api/jobs").json()}
    assert "Data Engineer" in titles


def test_repost_is_one_job_and_removed_posting_is_closed(client: TestClient, boards: FakeJobBoards) -> None:
    discover_boards(client, boards, ["acme"])
    run_to_completion(client)

    boards.serve("greenhouse", "acme", "acme-later")
    second = run_to_completion(client)

    jobs = client.get("/api/jobs").json()
    by_title = {job["title"]: job for job in jobs}
    assert sorted(job["title"] for job in jobs) == [
        "Data Engineer",
        "Site Reliability Engineer",
        "Software Engineer, Backend",
    ]
    assert by_title["Site Reliability Engineer"]["external_id"] == "4012345011"
    assert "5+ years of Python or Go" in by_title["Software Engineer, Backend"]["description"]
    assert second["updated_jobs"] == 1
    assert second["closed_jobs"] == 1


def test_failing_board_is_recorded_and_other_boards_still_complete(
    client: TestClient, boards: FakeJobBoards
) -> None:
    boards.fail("greenhouse", "broken", status=503)
    discover_boards(client, boards, ["broken", "acme"])

    run = run_to_completion(client)

    assert run["status"] == "finished"
    assert run["companies_fetched"] == 2
    assert run["errors"] == [
        {"kind": "board", "platform": "greenhouse", "board_id": "broken", "message": "The board returned HTTP 503."}
    ]
    assert len(client.get("/api/jobs").json()) == 3


def test_unknown_board_reports_not_found(client: TestClient, boards: FakeJobBoards) -> None:
    discover_boards(client, boards, ["no-such-board"])

    run = run_to_completion(client)

    assert run["errors"][0]["message"] == "Board not found (HTTP 404)."


def test_progress_is_visible_and_a_second_run_is_refused_while_one_is_active(
    client: TestClient, boards: FakeJobBoards
) -> None:
    release = boards.hold("greenhouse", "slow")
    discover_boards(client, boards, ["slow", "acme"])

    started = client.post("/api/runs")
    assert started.status_code == 202
    run_id = started.json()["id"]
    in_progress = wait_for_run(client, run_id, until=lambda run: run["companies_fetched"] == 1)
    assert in_progress["status"] == "running"
    assert in_progress["companies_total"] == 2
    assert in_progress["new_jobs"] == 3

    refused = client.post("/api/runs")
    assert refused.status_code == 409
    assert refused.json()["detail"] == "A run is already in progress."

    release.set()
    assert wait_for_run(client, run_id)["status"] == "finished"
    assert client.post("/api/runs").status_code == 202


def test_past_runs_are_listed_newest_first(client: TestClient, boards: FakeJobBoards) -> None:
    discover_boards(client, boards, ["acme"])
    first = run_to_completion(client)
    second = run_to_completion(client)

    runs = client.get("/api/runs").json()

    assert [run["id"] for run in runs] == [second["id"], first["id"]]


def test_closed_job_reopens_when_it_is_listed_again(client: TestClient, boards: FakeJobBoards) -> None:
    discover_boards(client, boards, ["acme"])
    run_to_completion(client)
    boards.serve("greenhouse", "acme", "acme-later")
    run_to_completion(client)

    boards.serve("greenhouse", "acme", "acme")
    third = run_to_completion(client)

    titles = {job["title"] for job in client.get("/api/jobs").json()}
    assert "Frontend Engineer" in titles
    assert third["new_jobs"] == 0
