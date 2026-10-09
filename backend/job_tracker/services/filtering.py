from collections import Counter

from job_tracker.models.job import Rejection, Rule
from job_tracker.repositories.unit_of_work import UnitOfWork
from job_tracker.services.filters import check


def refilter_jobs(uow: UnitOfWork, job_ids: list[int] | None = None) -> Counter[Rule]:
    """Re-check stored jobs (all open ones if `job_ids` is None) against the saved search settings.

    Records each job's verdict and returns how many were rejected by each rule.
    """
    settings = uow.settings.search_settings()
    rejected: Counter[Rule] = Counter()
    verdicts: list[tuple[int, Rejection | None]] = []
    for job in uow.jobs.open_jobs(job_ids):
        rejection = check(job.posting, settings)
        if rejection is not None:
            rejected[rejection.rule] += 1
        verdicts.append((job.id, rejection))
    uow.jobs.save_verdicts(verdicts)
    return rejected
