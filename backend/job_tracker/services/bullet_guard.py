"""The fact check on reworded experience bullets: a rewrite may change wording, never facts.

It runs on the tailor's rewrites and on my own edits alike, so a typo can't change a metric unnoticed either.
"""

import re
from collections import Counter

from job_tracker.services.keywords import mentions

MAX_GROWTH = 0.15

# "60%", "2M+", "9+", "1,200", "3.5x"
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*[kKmMbBx]?[%+]?")


def numbers(text: str) -> list[str]:
    return _NUMBER.findall(text)


def problem(original: str, rewrite: str, allowed_skills: list[str], keywords: list[str]) -> str | None:
    """Why `rewrite` can't replace `original` (the text after the bullet's label), or None when it can.

    It can't if its numbers differ from the original's (as a multiset), if it names a skill from the master list
    or the job's keywords that's in neither the original nor the master list, or if it's more than 15% longer.
    """
    before, after = Counter(numbers(original)), Counter(numbers(rewrite))
    if before != after:
        removed = [n for n in numbers(original) if (before - after)[n]]
        added = [n for n in numbers(rewrite) if (after - before)[n]]
        if removed and added:
            return f"It changes {', '.join(dict.fromkeys(removed))} to {', '.join(dict.fromkeys(added))}."
        if removed:
            return f"It drops {', '.join(dict.fromkeys(removed))}."
        return f"It adds the number {', '.join(dict.fromkeys(added))}."
    for skill in [*allowed_skills, *keywords]:
        listed = any(mentions(allowed, skill) for allowed in allowed_skills)
        if not listed and mentions(rewrite, skill) and not mentions(original, skill):
            return f"It adds “{skill}”, which isn't in this bullet or your master skills list."
    if len(rewrite) > len(original) * (1 + MAX_GROWTH):
        growth = round((len(rewrite) / len(original) - 1) * 100)
        return f"It's {growth}% longer than the original; a rewrite can grow by {round(MAX_GROWTH * 100)}% at most."
    return None
