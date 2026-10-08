from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import READY_SETTINGS, discover_boards, run_to_completion
from tests.fakes import FakeJobBoards, greenhouse_job

BOARD = "globex"
NYC = "New York, NY"


def job(title: str = "Backend Engineer", location: str = NYC, content: str = "<p>Join our team.</p>") -> dict[str, Any]:
    return greenhouse_job(BOARD, title, location, content)


def run_with(client: TestClient, boards: FakeJobBoards, jobs: list[dict[str, Any]], **settings: Any) -> dict[str, Any]:
    """Run against one board listing `jobs`, with the ready search settings plus `settings`."""
    boards.serve_jobs(BOARD, jobs)
    discover_boards(client, boards, [BOARD], {**READY_SETTINGS, **settings})
    return run_to_completion(client)


def shown(client: TestClient) -> list[str]:
    """Titles of the jobs that passed the filters, whether they're scored as matches yet or not."""
    passed = client.get("/api/jobs").json() + client.get("/api/jobs/below-threshold").json()
    return sorted(j["title"] for j in passed)


def rejections(client: TestClient) -> dict[str, tuple[str, str]]:
    """Filtered-out jobs by title: (rule, reason)."""
    return {
        j["title"]: (j["rejection"]["rule"], j["rejection"]["reason"])
        for j in client.get("/api/jobs/filtered-out").json()
    }


def test_title_must_match_one_of_my_roles(client: TestClient, boards: FakeJobBoards) -> None:
    run = run_with(
        client,
        boards,
        [
            job("Software Engineer, Back-end"),
            job("Senior Backend Engineer"),
            job("Backend Engineering Lead"),
            job("Frontend Engineer"),
        ],
        roles=["Backend Engineer"],
    )

    assert shown(client) == ["Backend Engineering Lead", "Senior Backend Engineer", "Software Engineer, Back-end"]
    assert rejections(client) == {"Frontend Engineer": ("role", "Title doesn't match any of your roles.")}
    assert run["filtered_out"]["role"] == 1
    assert sum(run["filtered_out"].values()) == 1


def test_title_must_not_contain_an_excluded_keyword(client: TestClient, boards: FakeJobBoards) -> None:
    run = run_with(
        client,
        boards,
        [job("Backend Engineer"), job("Backend Engineering Manager"), job("Principal Backend Engineer")],
        roles=["Backend"],
        excluded_keywords=["manager", "Principal"],
    )

    assert shown(client) == ["Backend Engineer"]
    assert rejections(client) == {
        "Backend Engineering Manager": ("excluded_keyword", "Title contains “manager”."),
        "Principal Backend Engineer": ("excluded_keyword", "Title contains “Principal”."),
    }
    assert run["filtered_out"]["excluded_keyword"] == 2


def test_location_must_be_one_of_mine(client: TestClient, boards: FakeJobBoards) -> None:
    run = run_with(
        client,
        boards,
        [job("Backend Engineer", "New York, New York, United States"), job("Backend Engineer II", "Austin, TX")],
        locations=[NYC],
        work_modes=["onsite"],
    )

    assert shown(client) == ["Backend Engineer"]
    assert rejections(client) == {"Backend Engineer II": ("location", "Austin, TX isn't one of your locations.")}
    assert run["filtered_out"]["location"] == 1


def test_remote_posting_passes_when_remote_is_chosen_even_outside_my_locations(
    client: TestClient, boards: FakeJobBoards
) -> None:
    run_with(client, boards, [job("Backend Engineer", "Remote - Canada")], locations=[NYC], work_modes=["remote"])

    assert shown(client) == ["Backend Engineer"]


def test_remote_posting_is_dropped_when_remote_is_not_chosen(client: TestClient, boards: FakeJobBoards) -> None:
    run_with(client, boards, [job("Backend Engineer", "Remote - US")], locations=[NYC], work_modes=["onsite"])

    assert rejections(client) == {"Backend Engineer": ("location", "Remote role, and you haven't chosen remote.")}


def test_hybrid_and_onsite_postings_pass_only_when_chosen(client: TestClient, boards: FakeJobBoards) -> None:
    postings = [job("Backend Engineer", "New York, NY (Hybrid)"), job("Backend Engineer II", NYC)]

    run_with(client, boards, postings, locations=[NYC], work_modes=["remote", "hybrid"])
    assert shown(client) == ["Backend Engineer"]
    assert rejections(client) == {
        "Backend Engineer II": ("location", "On-site role, and you haven't chosen on-site.")
    }

    client.put("/api/search-settings", json={**READY_SETTINGS, "locations": [NYC], "work_modes": ["onsite"]})
    assert shown(client) == ["Backend Engineer II"]
    assert rejections(client) == {"Backend Engineer": ("location", "Hybrid role, and you haven't chosen hybrid.")}


def test_titles_far_above_or_below_my_seniority_are_dropped(client: TestClient, boards: FakeJobBoards) -> None:
    titles = [
        "Backend Engineer",
        "Junior Backend Engineer",
        "Sr. Backend Engineer",
        "Staff Backend Engineer",
        "Backend Engineer Intern",
    ]
    run = run_with(client, boards, [job(t) for t in titles], seniority="mid")

    assert shown(client) == ["Backend Engineer", "Junior Backend Engineer", "Sr. Backend Engineer"]
    assert rejections(client) == {
        "Staff Backend Engineer": ("seniority", "Staff title, well above your level (mid-level)."),
        "Backend Engineer Intern": ("seniority", "Intern title, well below your level (mid-level)."),
    }
    assert run["filtered_out"]["seniority"] == 2


def test_postings_asking_for_far_more_or_far_fewer_years_are_dropped(
    client: TestClient, boards: FakeJobBoards
) -> None:
    postings = [
        job("Backend Engineer, Payments", content="<ul><li>4+ years of Python</li></ul>"),
        job("Backend Engineer, Search", content="<p>At least 8 years of software engineering experience.</p>"),
        job("Backend Engineer, Data", content="<p>1-2 years of experience with SQL.</p>"),
        job("Backend Engineer, Growth", content="<p>We've grown for 25 years. Some Go experience helps.</p>"),
    ]
    run = run_with(client, boards, postings, years_experience=3)

    assert shown(client) == ["Backend Engineer, Data", "Backend Engineer, Growth", "Backend Engineer, Payments"]
    assert rejections(client) == {
        "Backend Engineer, Search": ("experience", "Asks for 8+ years of experience; you have 3."),
    }
    assert run["filtered_out"]["experience"] == 1

    client.put("/api/search-settings", json={**READY_SETTINGS, "years_experience": 8})
    assert rejections(client) == {
        "Backend Engineer, Data": ("experience", "Asks for 1–2 years of experience; you have 8."),
    }


NO_SPONSORSHIP = [
    "<p>Note: no visa sponsorship is available for this position.</p>",
    "<p>We are unable to sponsor work visas at this time.</p>",
    "<p>You must be authorized to work in the US without current or future sponsorship.</p>",
    "<p>This role is not eligible for immigration sponsorship.</p>",
    "<p>Acme does not offer visa sponsorship.</p>",
]


def test_no_sponsorship_wording_is_dropped_only_when_i_need_sponsorship(
    client: TestClient, boards: FakeJobBoards
) -> None:
    postings = [job("Backend Engineer", content="<p>We sponsor visas, including H-1B transfers.</p>")]
    postings += [job(f"Backend Engineer {n}", content=text) for n, text in enumerate(NO_SPONSORSHIP)]

    run_with(client, boards, postings, needs_sponsorship=False)
    assert len(shown(client)) == 6

    client.put("/api/search-settings", json={**READY_SETTINGS, "needs_sponsorship": True})
    assert shown(client) == ["Backend Engineer"]
    assert set(rejections(client).values()) == {("sponsorship", "Says it doesn't sponsor visas.")}

    boards.serve_jobs(BOARD, [*postings, job("Backend Engineer, Infra", content=NO_SPONSORSHIP[0])])
    assert run_to_completion(client)["filtered_out"]["sponsorship"] == 1


def test_minimum_salary_applies_only_to_postings_that_list_pay(client: TestClient, boards: FakeJobBoards) -> None:
    postings = [
        job("Backend Engineer, Payments", content="<p>Competitive pay and equity.</p>"),
        job("Backend Engineer, Search", content="<p>The base salary range is $120,000 - $140,000 USD.</p>"),
        job("Backend Engineer, Data", content="<p>Pay: $140K–$185K plus equity.</p>"),
        job("Backend Engineer, Growth", content="<p>Contractors are paid $60 - $80 per hour.</p>"),
    ]
    run = run_with(client, boards, postings, min_salary=150000)

    assert shown(client) == ["Backend Engineer, Data", "Backend Engineer, Growth", "Backend Engineer, Payments"]
    assert rejections(client) == {
        "Backend Engineer, Search": ("salary", "Pays up to $140,000, below your $150,000 minimum."),
    }
    assert run["filtered_out"]["salary"] == 1
    salaries = {j["title"]: j["salary"] for j in client.get("/api/jobs").json()}
    assert salaries["Backend Engineer, Data"] == {"min": 140000, "max": 185000, "currency": "USD"}
    assert salaries["Backend Engineer, Payments"] is None
    assert salaries["Backend Engineer, Growth"] is None


def test_changing_settings_reapplies_filters_to_stored_jobs_without_fetching(
    client: TestClient, boards: FakeJobBoards
) -> None:
    run_with(client, boards, [job("Backend Engineer"), job("Frontend Engineer")], roles=["Backend Engineer"])
    boards.fetched_boards.clear()

    client.put("/api/search-settings", json={**READY_SETTINGS, "roles": ["Frontend Engineer"]})

    assert shown(client) == ["Frontend Engineer"]
    assert set(rejections(client)) == {"Backend Engineer"}
    assert boards.fetched_boards == []


def test_more_filters_round_trip(client: TestClient) -> None:
    defaults = client.get("/api/search-settings").json()
    assert defaults["excluded_keywords"] == []
    assert defaults["seniority"] is None
    assert defaults["years_experience"] is None
    assert defaults["needs_sponsorship"] is False
    assert defaults["min_salary"] is None

    more: dict[str, Any] = {
        "excluded_keywords": [" Manager ", "manager", "Principal"],
        "seniority": "senior",
        "years_experience": 6,
        "needs_sponsorship": True,
        "min_salary": 150000,
    }
    client.put("/api/search-settings", json={**READY_SETTINGS, **more})

    saved = client.get("/api/search-settings").json()
    assert saved["excluded_keywords"] == ["Manager", "Principal"]
    assert saved["seniority"] == "senior"
    assert saved["years_experience"] == 6
    assert saved["needs_sponsorship"] is True
    assert saved["min_salary"] == 150000


def test_more_filters_reject_nonsense_values(client: TestClient) -> None:
    for bad in ({"seniority": "wizard"}, {"years_experience": -1}, {"min_salary": -5}):
        assert client.put("/api/search-settings", json={**READY_SETTINGS, **bad}).status_code == 422
