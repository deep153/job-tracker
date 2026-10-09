import pytest

from job_tracker.utils.timestamps import utc_timestamp


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-30T14:02:11-04:00", "2026-09-30T18:02:11+00:00"),
        ("2026-09-30T18:02:11.123Z", "2026-09-30T18:02:11+00:00"),
        ("2026-09-30T18:02:11", "2026-09-30T18:02:11+00:00"),
        (1790791565000, "2026-09-30T18:06:05+00:00"),
    ],
)
def test_utc_timestamp(value: str | int, expected: str) -> None:
    assert utc_timestamp(value) == expected
