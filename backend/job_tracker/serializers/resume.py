from dataclasses import asdict
from typing import Any

from job_tracker.models.resume import ResumeVersion


def _urls(resume: ResumeVersion) -> dict[str, str]:
    base = f"/api/resume/versions/{resume.version}"
    return {"preview_url": f"{base}/preview.pdf", "original_url": f"{base}/original.docx"}


def resume_version_json(resume: ResumeVersion) -> dict[str, Any]:
    """A version as listed: without its paragraphs or mapping."""
    return {
        "version": resume.version,
        "filename": resume.filename,
        "uploaded_at": resume.uploaded_at,
        "page_count": resume.page_count,
        "ready": resume.ready,
        **_urls(resume),
    }


def resume_json(resume: ResumeVersion) -> dict[str, Any]:
    mapping = None
    if resume.mapped:
        mapping = {"summary": resume.summary_paragraphs, "skills": resume.skills_paragraphs}
    return {
        **resume_version_json(resume),
        "paragraphs": [asdict(p) for p in resume.paragraphs],
        "mapping": mapping,
        "skills": resume.skills,
    }
