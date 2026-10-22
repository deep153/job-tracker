"""The Profile Extractor: my contact details and links, found by code in my resume's text and link targets."""

import io
import re
from dataclasses import dataclass

import docx
from docx.opc.constants import RELATIONSHIP_TYPE as RT


@dataclass(frozen=True)
class Contact:
    email: str | None
    phone: str | None
    linkedin: str | None
    github: str | None
    website: str | None


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\w/])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
# A URL with a scheme or "www.", or a bare lower-case domain with a common ending (not "Node.js" or "B.Tech").
_URL = re.compile(
    r"(?:https?://|www\.)[^\s|,;()<>]+"
    r"|(?<![\w@.])[a-z0-9-]{2,}(?:\.[a-z0-9-]+)*\.(?:com|dev|io|me|net|org|app|ai|co|page|site|tech|xyz)"
    r"(?:/[^\s|,;()<>]*)?"
)


def hyperlinks(document: bytes) -> list[str]:
    """The targets of the document's links, in no particular order."""
    rels = docx.Document(io.BytesIO(document)).part.rels.values()
    return [rel.target_ref for rel in rels if rel.reltype == RT.HYPERLINK and rel.is_external]


def contact(texts: list[str], links: list[str]) -> Contact:
    """The first email, phone number, LinkedIn, GitHub and other website in the paragraphs' text or the link
    targets. Text comes first, since it's what I wrote; a link's target fills in what the text only names."""
    text = "\n".join(texts)
    emails = _EMAIL.findall(text) + [
        link.removeprefix("mailto:").split("?")[0] for link in links if link.startswith("mailto:")
    ]
    phones = _PHONE.findall(text)
    urls = [_url(found) for found in _URL.findall(_EMAIL.sub(" ", text))]
    urls += [_url(link) for link in links if link.startswith(("http://", "https://"))]
    linkedin = next((u for u in urls if "linkedin.com/" in u.casefold()), None)
    github = next((u for u in urls if "github.com/" in u.casefold()), None)
    website = next((u for u in urls if u not in (linkedin, github) and not _profile_site(u)), None)
    return Contact(
        email=emails[0] if emails else None,
        phone=" ".join(phones[0].split()) if phones else None,
        linkedin=linkedin,
        github=github,
        website=website,
    )


def _url(found: str) -> str:
    url = found.rstrip(".,;:)")
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def _profile_site(url: str) -> bool:
    return re.search(r"(linkedin|github)\.com", url, re.I) is not None
