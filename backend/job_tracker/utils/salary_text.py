import re

from job_tracker.models.posting import SalaryRange

_NUMBER = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kK])?"
# "$120,000 - $140,000", "$140K–$185K", "$150,000 to 180,000 USD"
_RANGE = re.compile(rf"\$\s?{_NUMBER}\s*(?:-|–|—|to)\s*\$?\s?{_NUMBER}(?P<after>[^.\n]{{0,25}})")
_NOT_ANNUAL = re.compile(r"\b(?:hour|hourly|hr|month|monthly|week|weekly|million|billion|mm?|bn?)\b", re.I)
_CURRENCY = re.compile(r"\b(USD|CAD|AUD|GBP|EUR|SGD)\b")
_MIN_ANNUAL_SALARY = 10_000


def salary_from_text(text: str) -> SalaryRange | None:
    """The first yearly pay range stated in a job description, if any."""
    for match in _RANGE.finditer(text):
        low = _amount(match[1], match[2])
        high = _amount(match[3], match[4])
        after = match["after"]
        if _NOT_ANNUAL.search(after) or not _MIN_ANNUAL_SALARY <= low <= high:
            continue
        currency = _CURRENCY.search(after)
        return SalaryRange(low, high, currency[1] if currency else "USD")
    return None


def _amount(number: str, thousands: str | None) -> int:
    value = float(number.replace(",", ""))
    return round(value * 1000 if thousands else value)
