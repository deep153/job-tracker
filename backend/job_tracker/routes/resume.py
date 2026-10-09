from typing import Any

from fastapi import APIRouter, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.serializers.resume import resume_json, resume_version_json
from job_tracker.services.resume_reader import MAX_UPLOAD_BYTES
from job_tracker.services.resume_service import MASTER_DOCX, PREVIEW_PDF
from job_tracker.validators.resume import ResumeMappingIn, ResumeSkillsIn

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.get("")
def get_resume(services: ServicesDep) -> dict[str, Any] | None:
    resume = services.resumes.current()
    return None if resume is None else resume_json(resume)


@router.post("", status_code=201)
async def upload_resume(file: UploadFile, services: ServicesDep) -> dict[str, Any]:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    resume = await run_in_threadpool(services.resumes.import_docx, file.filename or "", data)
    return resume_json(resume)


@router.put("/mapping")
def save_resume_mapping(body: ResumeMappingIn, services: ServicesDep) -> dict[str, Any]:
    return resume_json(services.resumes.save_mapping(body.summary, body.skills))


@router.put("/skills")
def save_resume_skills(body: ResumeSkillsIn, services: ServicesDep) -> dict[str, Any]:
    return resume_json(services.resumes.save_skills(body.skills))


@router.get("/versions")
def list_resume_versions(services: ServicesDep) -> list[dict[str, Any]]:
    return [resume_version_json(resume) for resume in services.resumes.versions()]


@router.get("/versions/{version}/preview.pdf")
def get_resume_preview(version: int, services: ServicesDep) -> FileResponse:
    return FileResponse(services.resumes.file(version, PREVIEW_PDF), media_type="application/pdf")


@router.get("/versions/{version}/original.docx")
def get_resume_original(version: int, services: ServicesDep) -> FileResponse:
    resume = services.resumes.get(version)
    return FileResponse(services.resumes.file(version, MASTER_DOCX), media_type=DOCX_TYPE, filename=resume.filename)
