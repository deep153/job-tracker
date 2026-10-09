from datetime import UTC, datetime


def utc_timestamp(value: str | int | float) -> str:
    """An ISO 8601 UTC timestamp to the second (e.g. "2026-09-30T18:02:11+00:00"), from ISO text or Unix
    epoch milliseconds, so timestamps from every platform sort correctly as text."""
    if isinstance(value, str):
        moment = datetime.fromisoformat(value)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
    else:
        moment = datetime.fromtimestamp(value / 1000, UTC)
    return moment.astimezone(UTC).replace(microsecond=0).isoformat()
