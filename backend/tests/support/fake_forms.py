"""A local web server for the fake application-form pages in `fixtures/forms`, so tests can point real
Playwright at them instead of at real company forms.

Posting a form records what was sent and redirects to `confirmation.html`. Query parameters on a page's URL pick
a variant: `captcha` adds a CAPTCHA placeholder to the form, and `fail` makes posting it show an error instead.
Additions go at the end of the form: before `<!-- form end -->` on pages that have it (forms without a <form>
element), else before `</form>`.
"""

import email
import email.policy
import threading
import urllib.parse
from dataclasses import dataclass, field
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

_PAGES = Path(__file__).parent.parent / "fixtures" / "forms"
_CAPTCHA = '<div class="g-recaptcha" data-sitekey="fake-site-key" style="width:304px;height:78px"></div>'
_FORM_END = "<!-- form end -->"
_FAILED = """<!doctype html><html><body>
<div role="alert" class="error-message">Something went wrong submitting your application. Please try again.</div>
</body></html>"""


@dataclass
class Submission:
    page: str
    fields: dict[str, str] = field(default_factory=dict)
    files: dict[str, tuple[str, bytes]] = field(default_factory=dict)  # by field: (file name, content)


_server: ThreadingHTTPServer | None = None
_lock = threading.Lock()
_submissions: list[Submission] = []
_added: list[str] = []


def form_url(page: str, **variants: bool) -> str:
    """The URL of `fixtures/forms/<page>`, with the given variants switched on; the server starts on first use
    and serves until the tests end."""
    global _server
    with _lock:
        if _server is None:
            _server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
            threading.Thread(target=_server.serve_forever, daemon=True).start()
        host, port = _server.server_address[:2]
    query = urllib.parse.urlencode({name: "1" for name, on in variants.items() if on})
    return f"http://{host!s}:{port}/{page}" + (f"?{query}" if query else "")


def submissions() -> list[Submission]:
    with _lock:
        return list(_submissions)


def add_to_forms(html: str) -> None:
    """From now on, serve every form with `html` added at its end, like a question added after review."""
    with _lock:
        _added.append(html)


def reset() -> None:
    with _lock:
        _submissions.clear()
        _added.clear()


def _parse_multipart(content_type: str, body: bytes) -> Submission:
    message: Message = email.message_from_bytes(
        f"Content-Type: {content_type}\r\n\r\n".encode() + body, policy=email.policy.compat32
    )
    sent = Submission(page="")
    for part in message.get_payload():
        assert isinstance(part, Message)
        name = part.get_param("name", header="content-disposition")
        assert isinstance(name, str)
        filename = part.get_filename()
        content = part.get_payload(decode=True)
        assert isinstance(content, bytes)
        if filename is not None:
            if filename:
                sent.files[name] = (filename, content)
        else:
            sent.fields[name] = content.decode()
    return sent


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send(self, status: int, body: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        for name, value in {"Content-Type": "text/html; charset=utf-8", **(headers or {})}.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urllib.parse.urlsplit(self.path)
        page = _PAGES / url.path.lstrip("/")
        if not page.is_file() or page.parent != _PAGES:
            self._send(404, b"<h1>Not found</h1>")
            return
        html = page.read_text()
        variants = urllib.parse.parse_qs(url.query)
        with _lock:
            added = "".join(_added)
        if "captcha" in variants:
            added += _CAPTCHA
        end = _FORM_END if _FORM_END in html else "</form>"
        html = html.replace(end, f"{added}{end}", 1)
        self._send(200, html.encode())

    def do_POST(self) -> None:
        url = urllib.parse.urlsplit(self.path)
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if "fail" in urllib.parse.parse_qs(url.query):
            self._send(200, _FAILED.encode())
            return
        sent = _parse_multipart(self.headers["Content-Type"], body)
        sent.page = url.path.lstrip("/")
        with _lock:
            _submissions.append(sent)
        self._send(303, headers={"Location": "/confirmation.html"})
