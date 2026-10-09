import json
import sqlite3
from dataclasses import asdict

from job_tracker.models.search_settings import SearchSettings


class SettingsRepository:
    """Single-user settings and secrets as key/value pairs."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def search_settings(self) -> SearchSettings:
        value = self.get("search")
        return SearchSettings(**json.loads(value)) if value else SearchSettings()

    def save_search_settings(self, settings: SearchSettings) -> None:
        self.set("search", json.dumps(asdict(settings)))
