import pytest

from job_tracker.clients.brave_search import SearchError
from job_tracker.models.company import DiscoveredBoard
from job_tracker.models.platform import Platform
from job_tracker.models.search_settings import SearchSettings
from job_tracker.services.discovery import MAX_SEARCH_QUERIES_PER_RUN, build_queries, discover, extract_board_id

GREENHOUSE_SITES = "(site:job-boards.greenhouse.io OR site:boards.greenhouse.io)"


class FakeSearch:
    def __init__(self, results: dict[str, list[str]] | None = None, error: SearchError | None = None) -> None:
        self._results = results or {}
        self._error = error
        self.queries: list[str] = []

    def search(self, query: str, api_key: str) -> list[str]:
        self.queries.append(query)
        if self._error:
            raise self._error
        return next((urls for site, urls in self._results.items() if site in query), [])


def test_queries_cover_every_role_place_and_platform_taking_turns() -> None:
    settings = SearchSettings(
        roles=["Backend Engineer"], locations=["New York, NY"], work_modes=["remote"], platforms=["greenhouse", "lever"]
    )

    assert build_queries(settings) == [
        ("greenhouse", f'{GREENHOUSE_SITES} "Backend Engineer" "New York, NY"'),
        ("lever", 'site:jobs.lever.co "Backend Engineer" "New York, NY"'),
        ("greenhouse", f'{GREENHOUSE_SITES} "Backend Engineer" "remote"'),
        ("lever", 'site:jobs.lever.co "Backend Engineer" "remote"'),
    ]


@pytest.mark.parametrize(
    ("platform", "url", "board_id"),
    [
        ("greenhouse", "https://job-boards.greenhouse.io/Acme/jobs/123", "acme"),
        ("greenhouse", "https://boards.eu.greenhouse.io/acme/jobs/123", "acme"),
        ("greenhouse", "https://boards.greenhouse.io/embed/job_board?for=acme", "acme"),
        ("greenhouse", "https://www.greenhouse.io/careers", None),
        ("lever", "https://jobs.lever.co/initech/5a1c7e52/apply", "initech"),
        ("lever", "https://jobs.eu.lever.co/umbrella/5a1c7e52", None),
        ("ashby", "https://jobs.ashbyhq.com/Hooli/8d2f5c1e?utm_source=x", "hooli"),
        ("ashby", "https://jobs.ashbyhq.com/", None),
        ("ashby", "https://jobs.ashbyhq.com/not%20a%20board", None),
    ],
)
def test_extract_board_id(platform: Platform, url: str, board_id: str | None) -> None:
    assert extract_board_id(platform, url) == board_id


def test_discover_keeps_each_board_once_with_the_query_that_found_it() -> None:
    search = FakeSearch(
        {"greenhouse": ["https://job-boards.greenhouse.io/acme/jobs/1", "https://job-boards.greenhouse.io/acme/jobs/2"]}
    )
    settings = SearchSettings(roles=["Backend Engineer"], locations=["New York, NY"], platforms=["greenhouse"])

    result = discover(search, "key", settings)

    assert result.boards == [DiscoveredBoard("greenhouse", "acme", search.queries[0])]
    assert (result.queries_made, result.capped, result.error) == (1, False, None)


def test_discover_stops_at_the_cap() -> None:
    roles = [f"Role {n}" for n in range(MAX_SEARCH_QUERIES_PER_RUN + 5)]
    search = FakeSearch()

    result = discover(search, "key", SearchSettings(roles=roles, locations=["NYC"], platforms=["greenhouse"]))

    assert len(search.queries) == result.queries_made == MAX_SEARCH_QUERIES_PER_RUN
    assert result.capped is True


def test_discover_stops_at_the_first_search_error() -> None:
    search = FakeSearch(error=SearchError("Brave rejected your search API key."))
    settings = SearchSettings(roles=["A", "B"], locations=["NYC"], platforms=["greenhouse"])

    result = discover(search, "key", settings)

    assert (result.queries_made, result.error) == (1, "Brave rejected your search API key.")
