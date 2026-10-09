from dataclasses import asdict
from typing import Any

from job_tracker.models.run import Run


def run_json(run: Run) -> dict[str, Any]:
    return asdict(run)
