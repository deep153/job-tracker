from fastapi.testclient import TestClient

from job_tracker.services.discovery import MAX_SEARCH_QUERIES_PER_RUN
from tests.support.api import READY_SETTINGS, SEARCH_KEY, configure_search, discover_boards, run_to_completion
from tests.support.fake_job_boards import FakeJobBoards

GREENHOUSE_SITES = "(site:job-boards.greenhouse.io OR site:boards.greenhouse.io)"


def test_search_combines_each_role_with_each_location_and_remote(client: TestClient, boards: FakeJobBoards) -> None:
    configure_search(
        client,
        {**READY_SETTINGS, "roles": ["Backend Engineer", "Platform Engineer"], "locations": ["New York, NY"]},
    )

    run = run_to_completion(client)

    assert boards.search_queries == [
        f'{GREENHOUSE_SITES} "Backend Engineer" "New York, NY"',
        f'{GREENHOUSE_SITES} "Backend Engineer" "remote"',
        f'{GREENHOUSE_SITES} "Platform Engineer" "New York, NY"',
        f'{GREENHOUSE_SITES} "Platform Engineer" "remote"',
    ]
    assert boards.search_keys == [SEARCH_KEY] * 4
    assert run["search_queries"] == 4


def test_board_ids_are_extracted_from_result_urls_once_each(client: TestClient, boards: FakeJobBoards) -> None:
    configure_search(client)
    boards.search_returns(
        [
            "https://job-boards.greenhouse.io/acme/jobs/4012345008",
            "https://boards.greenhouse.io/Acme/jobs/4012345009?gh_src=abc",
            "https://boards.greenhouse.io/embed/job_app?for=globex&token=123",
            "https://job-boards.eu.greenhouse.io/northwind",
            "https://www.linkedin.com/jobs/view/12345",
            "https://greenhouse.io/blog/hiring-tips",
        ]
    )

    run = run_to_completion(client)

    companies = client.get("/api/companies").json()
    assert sorted(c["board_id"] for c in companies) == ["acme", "globex", "northwind"]
    assert run["companies_discovered"] == 3
    acme = next(c for c in companies if c["board_id"] == "acme")
    assert acme["platform"] == "greenhouse"
    assert acme["discovered_query"] == f'{GREENHOUSE_SITES} "Backend Engineer" "New York, NY"'
    assert acme["open_jobs"] == 3
    assert acme["blocked"] is False


def test_discovered_companies_are_fetched_on_later_runs_without_searching_them_again(
    client: TestClient, boards: FakeJobBoards
) -> None:
    discover_boards(client, boards, ["acme"])
    run_to_completion(client)

    boards.search_returns([])
    second = run_to_completion(client)

    assert second["companies_discovered"] == 0
    assert second["companies_total"] == 1
    assert len(client.get("/api/jobs").json()) == 3


def test_blocked_company_is_never_fetched_again_and_its_jobs_are_hidden(
    client: TestClient, boards: FakeJobBoards
) -> None:
    discover_boards(client, boards, ["acme", "globex"])
    run_to_completion(client)
    acme = next(c for c in client.get("/api/companies").json() if c["board_id"] == "acme")

    blocked = client.patch(f"/api/companies/{acme['id']}", json={"blocked": True})
    assert blocked.json()["blocked"] is True
    assert all(job["company"] != "acme" for job in client.get("/api/jobs").json())

    boards.fetched_boards.clear()
    run = run_to_completion(client)

    assert ("greenhouse", "acme") not in boards.fetched_boards
    assert run["companies_total"] == 1
    assert run["companies_discovered"] == 0

    client.patch(f"/api/companies/{acme['id']}", json={"blocked": False})
    assert any(job["company"] == "acme" for job in client.get("/api/jobs").json())


def test_search_failure_is_reported_and_known_companies_are_still_fetched(
    client: TestClient, boards: FakeJobBoards
) -> None:
    discover_boards(client, boards, ["acme"])
    run_to_completion(client)

    boards.fail_search(401)
    boards.search_queries.clear()
    run = run_to_completion(client)

    assert run["status"] == "finished"
    assert len(boards.search_queries) == 1
    assert run["errors"] == [
        {
            "kind": "search",
            "platform": None,
            "board_id": None,
            "message": "The search API rejected your key (HTTP 401). Check the key in Search settings.",
        }
    ]
    assert run["companies_fetched"] == 1
    assert len(client.get("/api/jobs").json()) == 3


def test_search_queries_per_run_are_capped(client: TestClient, boards: FakeJobBoards) -> None:
    roles = [f"Role {n}" for n in range(6)]
    locations = [f"City {n}" for n in range(4)]
    configure_search(client, {**READY_SETTINGS, "roles": roles, "locations": locations})

    run = run_to_completion(client)

    assert len(boards.search_queries) == MAX_SEARCH_QUERIES_PER_RUN
    assert run["search_queries"] == MAX_SEARCH_QUERIES_PER_RUN
    assert run["search_queries_capped"] is True


def test_greenhouse_disabled_means_nothing_is_searched_or_fetched(client: TestClient, boards: FakeJobBoards) -> None:
    discover_boards(client, boards, ["acme"])
    run_to_completion(client)
    boards.search_queries.clear()
    boards.fetched_boards.clear()

    client.put("/api/search-settings", json={**READY_SETTINGS, "platforms": []})

    assert client.post("/api/runs").status_code == 400
    assert boards.search_queries == []
    assert boards.fetched_boards == []
