from typing import Any

from fastapi.testclient import TestClient

from job_tracker.services.discovery import MAX_SEARCH_QUERIES_PER_RUN
from tests.support.api import BROAD_SETTINGS, READY_SETTINGS, configure_search, run_to_completion
from tests.support.fake_job_boards import FakeJobBoards, ashby_job_url, greenhouse_job_url, lever_job_url

ALL_PLATFORMS = ["greenhouse", "lever", "ashby"]
GREENHOUSE_SITES = "(site:job-boards.greenhouse.io OR site:boards.greenhouse.io)"


def discover_all(client: TestClient, boards: FakeJobBoards, **settings: Any) -> None:
    """A ready search on all three platforms whose results point at one board on each."""
    configure_search(client, {**BROAD_SETTINGS, "platforms": ALL_PLATFORMS, **settings})
    boards.search_returns([greenhouse_job_url("acme"), lever_job_url("initech"), ashby_job_url("hooli")])


def jobs_by_title(client: TestClient) -> dict[str, dict[str, Any]]:
    """The jobs that passed the filters, whether they're scored as matches yet or not."""
    passed = client.get("/api/jobs").json() + client.get("/api/jobs/below-threshold").json()
    return {job["title"]: job for job in passed}


def rejections(client: TestClient) -> dict[str, tuple[str, str]]:
    return {
        j["title"]: (j["rejection"]["rule"], j["rejection"]["reason"])
        for j in client.get("/api/jobs/filtered-out").json()
    }


def test_run_with_all_three_platforms_stores_jobs_from_each(client: TestClient, boards: FakeJobBoards) -> None:
    discover_all(client, boards)

    run = run_to_completion(client)

    assert run["status"] == "finished"
    assert run["errors"] == []
    assert run["companies_total"] == 3
    platforms = {(job["company"], job["title"]): job["platform"] for job in client.get("/api/jobs").json()}
    assert platforms == {
        ("acme", "Software Engineer, Backend"): "greenhouse",
        ("acme", "Frontend Engineer"): "greenhouse",
        ("acme", "Site Reliability Engineer"): "greenhouse",
        ("initech", "Backend Engineer"): "lever",
        ("initech", "Platform Engineer"): "lever",
        ("initech", "Support Engineer"): "lever",
        ("hooli", "Senior Software Engineer"): "ashby",
        ("hooli", "Machine Learning Engineer"): "ashby",
        ("hooli", "Data Engineer"): "ashby",
    }
    assert "Infrastructure Engineer" not in jobs_by_title(client)  # unlisted on Ashby
    open_jobs = {c["board_id"]: c["open_jobs"] for c in client.get("/api/companies").json()}
    assert open_jobs == {"acme": 3, "initech": 3, "hooli": 3}


def test_lever_postings_are_normalized(client: TestClient, boards: FakeJobBoards) -> None:
    discover_all(client, boards)
    run_to_completion(client)
    jobs = jobs_by_title(client)

    backend = jobs["Backend Engineer"]
    assert backend["external_id"] == "5a1c7e52-2c9b-4c8f-9a51-0f3e2b7d1a01"
    assert backend["locations"] == ["New York, New York"]
    assert backend["remote"] is False
    assert backend["work_mode"] == "hybrid"
    assert backend["salary"] == {"min": 160000, "max": 190000, "currency": "USD"}
    assert backend["posting_url"] == "https://jobs.lever.co/initech/5a1c7e52-2c9b-4c8f-9a51-0f3e2b7d1a01"
    assert backend["application_url"] == "https://jobs.lever.co/initech/5a1c7e52-2c9b-4c8f-9a51-0f3e2b7d1a01/apply"
    assert backend["updated_at"] == "2026-10-01T12:00:00+00:00"
    description = backend["description"]
    assert "Initech is hiring a backend engineer" in description
    assert "What you'll do" in description and "- Build services in Go & Python." in description
    assert "- 3+ years of backend experience" in description
    assert description.endswith("Initech is an equal opportunity employer.")
    assert "<" not in description

    platform = jobs["Platform Engineer"]
    assert platform["remote"] is True
    assert platform["work_mode"] == "remote"
    assert platform["salary"] is None

    assert jobs["Support Engineer"]["work_mode"] == "onsite"
    assert jobs["Support Engineer"]["salary"] is None  # hourly pay isn't a yearly salary


def test_ashby_postings_are_normalized(client: TestClient, boards: FakeJobBoards) -> None:
    discover_all(client, boards)
    run_to_completion(client)
    jobs = jobs_by_title(client)

    senior = jobs["Senior Software Engineer"]
    assert senior["external_id"] == "8d2f5c1e-6b7a-4e3d-9f10-2a4b6c8d0e01"
    assert senior["locations"] == ["New York, NY", "San Francisco, CA"]
    assert senior["remote"] is False
    assert senior["work_mode"] == "hybrid"
    assert senior["salary"] == {"min": 120000, "max": 140000, "currency": "USD"}
    assert senior["posting_url"] == "https://jobs.ashbyhq.com/hooli/8d2f5c1e-6b7a-4e3d-9f10-2a4b6c8d0e01"
    assert senior["application_url"] == (
        "https://jobs.ashbyhq.com/hooli/8d2f5c1e-6b7a-4e3d-9f10-2a4b6c8d0e01/application"
    )
    assert senior["updated_at"] == "2026-10-02T11:00:00+00:00"
    assert "Hooli is making the world a better place." in senior["description"]
    assert "<" not in senior["description"]

    ml = jobs["Machine Learning Engineer"]
    assert ml["locations"] == ["Remote (US)"]
    assert ml["remote"] is True
    assert ml["work_mode"] == "remote"
    assert ml["salary"] is None
    assert ml["updated_at"] == "2026-09-28T16:07:45+00:00"

    data = jobs["Data Engineer"]
    assert data["work_mode"] == "onsite"
    assert data["salary"] is None  # equity only


def test_jobs_from_all_platforms_sort_together_by_time(client: TestClient, boards: FakeJobBoards) -> None:
    discover_all(client, boards)
    run_to_completion(client)

    # Greenhouse states local offsets ("09:15:00-04:00" is 13:15 UTC), so it must sort after conversion to UTC.
    assert [job["title"] for job in client.get("/api/jobs").json()] == [
        "Frontend Engineer",  # Greenhouse, 2026-10-02 13:15 UTC
        "Senior Software Engineer",  # Ashby, 2026-10-02 11:00 UTC
        "Backend Engineer",  # Lever, 2026-10-01 12:00 UTC
        "Software Engineer, Backend",
        "Machine Learning Engineer",
        "Platform Engineer",
        "Data Engineer",
        "Site Reliability Engineer",
        "Support Engineer",
    ]
    assert all(job["updated_at"].endswith("+00:00") for job in client.get("/api/jobs").json())


def test_lever_and_ashby_board_ids_are_extracted_from_result_urls(client: TestClient, boards: FakeJobBoards) -> None:
    configure_search(client, {**READY_SETTINGS, "platforms": ALL_PLATFORMS})
    boards.search_returns(
        [
            "https://jobs.lever.co/initech/5a1c7e52-2c9b-4c8f-9a51-0f3e2b7d1a01/apply",
            "https://jobs.lever.co/Initech?lever-via=abc",
            "https://jobs.eu.lever.co/umbrella/5a1c7e52",
            "https://www.lever.co/blog",
            "https://jobs.ashbyhq.com/hooli/8d2f5c1e-6b7a-4e3d-9f10-2a4b6c8d0e01?utm_source=x",
            "https://jobs.ashbyhq.com/Hooli/8d2f5c1e-6b7a-4e3d-9f10-2a4b6c8d0e01/application",
            "https://www.ashbyhq.com/customers",
            "https://jobs.ashbyhq.com/",
        ]
    )

    run = run_to_completion(client)

    companies = {(c["platform"], c["board_id"]): c for c in client.get("/api/companies").json()}
    assert set(companies) == {("lever", "initech"), ("ashby", "hooli")}
    assert run["companies_discovered"] == 2
    assert companies[("lever", "initech")]["discovered_query"] == 'site:jobs.lever.co "Backend Engineer" "New York, NY"'
    assert companies[("ashby", "hooli")]["discovered_query"] == (
        'site:jobs.ashbyhq.com "Backend Engineer" "New York, NY"'
    )


def test_each_enabled_platform_is_searched_for_every_role_and_place(client: TestClient, boards: FakeJobBoards) -> None:
    configure_search(client, {**READY_SETTINGS, "platforms": ALL_PLATFORMS})

    run_to_completion(client)

    assert boards.search_queries == [
        f'{GREENHOUSE_SITES} "Backend Engineer" "New York, NY"',
        'site:jobs.lever.co "Backend Engineer" "New York, NY"',
        'site:jobs.ashbyhq.com "Backend Engineer" "New York, NY"',
        f'{GREENHOUSE_SITES} "Backend Engineer" "remote"',
        'site:jobs.lever.co "Backend Engineer" "remote"',
        'site:jobs.ashbyhq.com "Backend Engineer" "remote"',
    ]


def test_capped_searches_are_shared_between_platforms(client: TestClient, boards: FakeJobBoards) -> None:
    roles = [f"Role {n}" for n in range(6)]
    configure_search(client, {**READY_SETTINGS, "roles": roles, "platforms": ALL_PLATFORMS})

    run_to_completion(client)

    assert len(boards.search_queries) == MAX_SEARCH_QUERIES_PER_RUN
    per_site = {site: sum(site in q for q in boards.search_queries) for site in ("greenhouse", "lever", "ashby")}
    assert per_site == {"greenhouse": 7, "lever": 7, "ashby": 6}


def test_disabling_a_platform_stops_its_discovery_and_fetching(client: TestClient, boards: FakeJobBoards) -> None:
    discover_all(client, boards)
    run_to_completion(client)
    boards.search_queries.clear()
    boards.fetched_boards.clear()

    client.put("/api/search-settings", json={**BROAD_SETTINGS, "platforms": ["greenhouse", "ashby"]})
    run = run_to_completion(client)

    assert not any("lever" in query for query in boards.search_queries)
    assert sorted(boards.fetched_boards) == [("ashby", "hooli"), ("greenhouse", "acme")]
    assert run["companies_total"] == 2

    boards.search_queries.clear()
    boards.fetched_boards.clear()
    client.put("/api/search-settings", json={**BROAD_SETTINGS, "platforms": ["lever"]})
    run_to_completion(client)

    assert all(query.startswith("site:jobs.lever.co") for query in boards.search_queries)
    assert boards.fetched_boards == [("lever", "initech")]


def test_lever_and_ashby_salaries_feed_the_minimum_salary_filter(client: TestClient, boards: FakeJobBoards) -> None:
    discover_all(client, boards, min_salary=150000)

    run = run_to_completion(client)

    assert rejections(client) == {
        "Senior Software Engineer": ("salary", "Pays up to $140,000, below your $150,000 minimum."),
    }
    assert run["filtered_out"]["salary"] == 1
    assert "Backend Engineer" in jobs_by_title(client)  # Lever, $160K–$190K

    client.put("/api/search-settings", json={**BROAD_SETTINGS, "platforms": ALL_PLATFORMS, "min_salary": 200000})
    assert rejections(client)["Backend Engineer"] == ("salary", "Pays up to $190,000, below your $200,000 minimum.")


def test_work_mode_stated_by_the_platform_drives_the_location_filter(client: TestClient, boards: FakeJobBoards) -> None:
    discover_all(client, boards, platforms=["lever", "ashby"], work_modes=["onsite"])
    run_to_completion(client)

    assert sorted(jobs_by_title(client)) == ["Data Engineer", "Platform Engineer", "Support Engineer"]
    assert rejections(client) == {
        "Backend Engineer": ("location", "Hybrid role, and you haven't chosen hybrid."),
        "Senior Software Engineer": ("location", "Hybrid role, and you haven't chosen hybrid."),
        "Machine Learning Engineer": ("location", "Remote role, and you haven't chosen remote."),
    }

    client.put(
        "/api/search-settings", json={**BROAD_SETTINGS, "platforms": ["lever", "ashby"], "work_modes": ["hybrid"]}
    )
    assert sorted(jobs_by_title(client)) == ["Backend Engineer", "Platform Engineer", "Senior Software Engineer"]
    assert rejections(client)["Support Engineer"] == ("location", "On-site role, and you haven't chosen on-site.")
