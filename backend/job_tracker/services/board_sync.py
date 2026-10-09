import hashlib
import json
from dataclasses import dataclass, field

from job_tracker.models.platform import Platform
from job_tracker.models.posting import Posting
from job_tracker.repositories.job_repository import JobRepository


@dataclass
class SyncResult:
    new: int = 0
    updated: int = 0
    closed: int = 0
    # New, changed and reopened jobs: the ones whose filter verdict may have changed.
    to_filter: list[int] = field(default_factory=list)


def content_hash(posting: Posting) -> str:
    """Identifies a posting by what it says, so a repost under a new ID is recognized."""
    content = json.dumps([posting.title.strip(), posting.locations, posting.description.strip()])
    return hashlib.sha256(content.encode()).hexdigest()


def sync_board(
    jobs: JobRepository, platform: Platform, board_id: str, postings: list[Posting], seen_at: str
) -> SyncResult:
    """Bring stored jobs for one board in line with what the board lists right now."""
    result = SyncResult()
    seen: set[int] = set()
    for posting in postings:
        digest = content_hash(posting)
        existing = jobs.find_by_external_id(platform, posting.external_id)
        if existing is None:
            existing = jobs.find_by_content(platform, board_id, digest)
            if existing is not None and existing.id in seen:
                continue  # the same job listed twice on this board
        if existing is None:
            job_id = jobs.insert(posting, digest, seen_at)
            seen.add(job_id)
            result.new += 1
            result.to_filter.append(job_id)
            continue
        if existing.content_hash != digest:
            result.updated += 1
        if existing.content_hash != digest or existing.closed:
            result.to_filter.append(existing.id)
        jobs.update(existing.id, posting, digest, seen_at)
        seen.add(existing.id)

    gone = [job_id for job_id in jobs.open_ids(platform, board_id) if job_id not in seen]
    jobs.close(gone)
    result.closed = len(gone)
    return result
