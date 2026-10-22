"""Loose keyword matching: whether a text mentions a skill, ignoring case, punctuation and plurals."""

import re


def terms(text: str) -> list[str]:
    """Lower-cased words without punctuation, plurals folded ("APIs" is "api")."""
    words = re.findall(r"[\w+#]+", text.casefold())
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words]


def mentions(text: str, keyword: str) -> bool:
    """Whether `text` mentions `keyword` as whole words. A keyword with a parenthetical ("AWS (Lambda)") counts as
    the term before it."""
    wanted = terms(keyword.split("(")[0]) or terms(keyword)
    have, n = terms(text), len(wanted)
    return bool(wanted) and any(have[i : i + n] == wanted for i in range(len(have) - n + 1))


def covered(keywords: list[str], text: str) -> list[bool]:
    """Which keywords the text mentions."""
    return [mentions(text, keyword) for keyword in keywords]
