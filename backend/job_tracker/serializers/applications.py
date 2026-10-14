from dataclasses import asdict
from typing import Any

from job_tracker.models.answers import FormAnswer
from job_tracker.models.application import Application, TailoredResume
from job_tracker.models.job import Job
from job_tracker.serializers.jobs import job_json


def _resume_json(application_id: int, resume: TailoredResume) -> dict[str, Any]:
    keywords = [
        {"keyword": keyword, "before": before, "after": after}
        for keyword, before, after in zip(resume.keywords, resume.covered_before, resume.covered_after, strict=True)
    ]
    base = f"/api/applications/{application_id}"
    return {
        "master_version": resume.master_version,
        "summary": {"master": resume.master_summary, "tailored": resume.summary},
        "skills": {
            "master": [asdict(line) for line in resume.master_skills],
            "tailored": [asdict(line) for line in resume.skills],
        },
        "page_count": resume.page_count,
        "master_page_count": resume.master_page_count,
        "fits": resume.page_count <= resume.master_page_count,
        "coverage": {
            "keywords": keywords,
            "before": sum(resume.covered_before),
            "after": sum(resume.covered_after),
            "total": len(resume.keywords),
        },
        "pdf_url": f"{base}/resume.pdf",
        "docx_url": f"{base}/resume.docx",
    }


def application_json(application: Application, job: Job) -> dict[str, Any]:
    """The application with everything the review screen shows."""
    return {
        "id": application.id,
        "status": application.status,
        "error": application.error,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "cost_usd": application.cost_usd,
        "job": job_json(job),
        "resume": None if application.resume is None else _resume_json(application.id, application.resume),
        "questions": None if application.answers is None else [_question_json(a) for a in application.answers],
        "cover_letter": _cover_letter_json(application),
        "form_error": application.form_error,
        "submitted_at": application.submitted_at,
        "screenshot_url": f"/api/applications/{application.id}/screenshot.png" if application.screenshot else None,
        "can_approve": application.approval_problem is None,
        "approval_problem": application.approval_problem,
    }


def application_summary_json(application: Application, job: Job) -> dict[str, Any]:
    """A row in the applications list; `date` is when it was submitted, or started if it hasn't been."""
    return {
        "id": application.id,
        "status": application.status,
        "date": application.submitted_at or application.created_at,
        "job": job_json(job),
    }


def _cover_letter_json(application: Application) -> dict[str, Any] | None:
    if application.cover_letter is None:
        return None
    pdf_url = f"/api/applications/{application.id}/cover-letter.pdf" if application.cover_letter_file else None
    return {"text": application.cover_letter, "pdf_url": pdf_url}


def _question_json(answer: FormAnswer) -> dict[str, Any]:
    return {
        **asdict(answer.field),
        "answer": answer.answer,
        "source": answer.source,
        "eeo": answer.eeo,
        "needs_input": answer.needs_input,
    }
