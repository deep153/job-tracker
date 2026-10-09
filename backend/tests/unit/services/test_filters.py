import pytest

from job_tracker.models.job import Rejection
from job_tracker.models.posting import SalaryRange
from job_tracker.models.search_settings import SearchSettings
from job_tracker.services.filters import check, refuses_sponsorship, required_years, title_level
from tests.support.builders import posting

SETTINGS = SearchSettings(
    roles=["Backend Engineer"],
    locations=["New York, NY"],
    work_modes=["remote", "hybrid", "onsite"],
    platforms=["greenhouse"],
)


def test_a_posting_that_breaks_no_rule_passes() -> None:
    assert check(posting(), SETTINGS) is None


@pytest.mark.parametrize(
    ("title", "passes"),
    [
        ("Senior Back-end Engineer", True),
        ("Engineer, Backend Systems", True),
        ("Backend Engineering Lead", True),
        ("Frontend Engineer", False),
    ],
)
def test_role_matches_title_words_in_any_order_and_form(title: str, passes: bool) -> None:
    rejection = check(posting(title=title), SETTINGS)
    assert (rejection is None) == passes, rejection


def test_excluded_keywords_reject_by_title() -> None:
    settings = SearchSettings(**{**SETTINGS.__dict__, "excluded_keywords": ["Manager"]})

    rejection = check(posting(title="Backend Engineering Manager"), settings)

    assert rejection == Rejection("excluded_keyword", "Title contains “Manager”.")


def test_locations_outside_mine_are_rejected_unless_remote() -> None:
    assert check(posting(locations=["Austin, TX"]), SETTINGS) == Rejection(
        "location", "Austin, TX isn't one of your locations."
    )
    assert check(posting(locations=["Austin, TX"], remote=True), SETTINGS) is None
    assert check(posting(locations=["New York City"]), SETTINGS) is None


def test_work_mode_must_be_one_i_chose() -> None:
    onsite_only = SearchSettings(**{**SETTINGS.__dict__, "work_modes": ["onsite"]})

    assert check(posting(work_mode="hybrid"), onsite_only) == Rejection(
        "location", "Hybrid role, and you haven't chosen hybrid."
    )
    assert check(posting(title="Backend Engineer (Hybrid)"), onsite_only) == Rejection(
        "location", "Hybrid role, and you haven't chosen hybrid."
    )


def test_salary_below_my_minimum_is_rejected_only_in_usd() -> None:
    settings = SearchSettings(**{**SETTINGS.__dict__, "min_salary": 150_000})

    assert check(posting(salary=SalaryRange(120_000, 140_000, "USD")), settings) == Rejection(
        "salary", "Pays up to $140,000, below your $150,000 minimum."
    )
    assert check(posting(salary=SalaryRange(120_000, 160_000, "USD")), settings) is None
    assert check(posting(salary=SalaryRange(100_000, 120_000, "GBP")), settings) is None
    assert check(posting(salary=None), settings) is None


@pytest.mark.parametrize(
    ("title", "level"),
    [
        ("Senior Backend Engineer", "senior"),
        ("Sr. Software Engineer", "senior"),
        ("Staff Engineer", "staff"),
        ("Associate Director, Engineering", "director"),
        ("Software Engineer II", "mid"),
        ("Software Engineer III", "senior"),
        ("New Grad Software Engineer", "junior"),
        ("Software Engineering Intern", "intern"),
        ("Backend Engineer", None),
    ],
)
def test_title_level(title: str, level: str | None) -> None:
    assert title_level(title) == level


def test_titles_far_from_my_level_are_rejected() -> None:
    senior = SearchSettings(**{**SETTINGS.__dict__, "seniority": "senior"})

    assert check(posting(title="Staff Backend Engineer"), senior) is None
    assert check(posting(title="Principal Backend Engineer"), senior) == Rejection(
        "seniority", "Principal title, well above your level (senior)."
    )
    assert check(posting(title="Junior Backend Engineer"), senior) == Rejection(
        "seniority", "Junior title, well below your level (senior)."
    )


@pytest.mark.parametrize(
    ("text", "years"),
    [
        ("5+ years of backend experience", (5, None)),
        ("3-5 years experience", (3, 5)),
        ("at least 8 years building systems", (8, None)),
        ("2 years of Python; 6+ years of software", (6, None)),
        ("We've been around for 25 years.", None),
        ("Founded 10 years ago", None),
    ],
)
def test_required_years(text: str, years: tuple[int, int | None] | None) -> None:
    assert required_years(text) == years


def test_experience_far_from_mine_is_rejected() -> None:
    settings = SearchSettings(**{**SETTINGS.__dict__, "years_experience": 3})

    assert check(posting(description="5+ years of experience"), settings) is None
    assert check(posting(description="8+ years of experience"), settings) == Rejection(
        "experience", "Asks for 8+ years of experience; you have 3."
    )


@pytest.mark.parametrize(
    ("text", "refuses"),
    [
        ("We are unable to sponsor visas for this role.", True),
        ("No visa sponsorship is available.", True),
        ("Candidates must be authorized to work without sponsorship now or in the future.", True),
        ("Sponsorship is not available.", True),
        ("We sponsor visas.", False),
        ("Visa sponsorship available.", False),
    ],
)
def test_refuses_sponsorship(text: str, refuses: bool) -> None:
    assert refuses_sponsorship(text) == refuses
