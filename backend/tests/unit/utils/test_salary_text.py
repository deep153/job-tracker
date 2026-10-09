import pytest

from job_tracker.models.posting import SalaryRange
from job_tracker.utils.salary_text import salary_from_text


@pytest.mark.parametrize(
    ("text", "salary"),
    [
        ("Pay: $120,000 - $140,000 per year.", SalaryRange(120_000, 140_000, "USD")),
        ("$140K–$185K", SalaryRange(140_000, 185_000, "USD")),
        ("$150,000 to 180,000 CAD", SalaryRange(150_000, 180_000, "CAD")),
        ("$40 - $60 per hour", None),
        ("We raised $10 - $20 million", None),
        ("No pay range here.", None),
    ],
)
def test_salary_from_text(text: str, salary: SalaryRange | None) -> None:
    assert salary_from_text(text) == salary
