"""A local web server for the fake application-form pages in `fixtures/forms`, so tests can point real
Playwright at them instead of at real company forms."""

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

_PAGES = Path(__file__).parent.parent / "fixtures" / "forms"
_server: ThreadingHTTPServer | None = None
_lock = threading.Lock()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass


def form_url(page: str) -> str:
    """The URL of `fixtures/forms/<page>`; the server starts on first use and serves until the tests end."""
    global _server
    with _lock:
        if _server is None:
            handler = functools.partial(_QuietHandler, directory=str(_PAGES))
            _server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=_server.serve_forever, daemon=True).start()
        host, port = _server.server_address[:2]
    return f"http://{host!s}:{port}/{page}"
