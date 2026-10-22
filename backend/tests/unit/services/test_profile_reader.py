from job_tracker.models.profile import Education
from job_tracker.services.profile_reader import degree_in_full, month_name, preferred, proper_case


def test_names_in_capitals_or_lowercase_are_proper_cased() -> None:
    assert proper_case("DEEP  GANDHI") == "Deep Gandhi"
    assert proper_case("o'brien-smith") == "O'Brien-Smith"
    assert proper_case("McKenzie") == "McKenzie"  # mixed case is kept as written


def test_abbreviated_degrees_are_written_in_full() -> None:
    assert degree_in_full("B.Tech.") == "Bachelor of Technology"
    assert degree_in_full("M.S.") == "Master of Science"
    assert degree_in_full("Ph.D") == "Doctor of Philosophy"
    assert degree_in_full("Master of Science") == "Master of Science"


def test_months_are_full_names() -> None:
    assert [month_name(m) for m in ["05", "5", "Sept.", "may", "Spring"]] == [
        "May",
        "May",
        "September",
        "May",
        "Spring",
    ]


def entry(degree: str, year: str, month: str = "May") -> Education:
    return Education("A University", degree, "Computer Science", month, year)


def test_the_highest_degree_is_preferred_then_the_most_recent() -> None:
    assert preferred([entry("Bachelor of Science", "2021"), entry("Master of Science", "2019")]) == 1
    assert preferred([entry("Master of Arts", "2018"), entry("Master of Science", "2022")]) == 1
    assert preferred([entry("Certificate", "2023"), entry("Bachelor of Arts", "2016")]) == 1
    assert preferred([entry("Bachelor of Arts", "2016", "May"), entry("Bachelor of Science", "2016", "June")]) == 1
    assert preferred([]) is None
