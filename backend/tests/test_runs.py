from job_tracker.companies import Company
from tests.conftest import MakeClient

ACME = Company(platform="greenhouse", board_id="acme")


def test_run_fetches_greenhouse_postings_into_jobs_list(make_client: MakeClient) -> None:
    client = make_client([ACME])

    run = client.post("/api/runs")
    assert run.status_code == 201
    assert run.json()["started_at"] is not None
    assert run.json()["finished_at"] is not None

    jobs = client.get("/api/jobs").json()
    by_title = {job["title"]: job for job in jobs}
    assert set(by_title) == {"Software Engineer, Backend", "Frontend Engineer"}

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


def test_no_jobs_before_first_run(make_client: MakeClient) -> None:
    client = make_client([ACME])

    assert client.get("/api/jobs").json() == []
