from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, JSONResponse

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.routes.resume import DOCX_TYPE
from job_tracker.serializers.applications import application_json
from job_tracker.services.application_service import TAILORED_DOCX, TAILORED_PDF
from job_tracker.validators.applications import TailoredResumeIn

router = APIRouter(prefix="/api", tags=["applications"])


@router.post("/jobs/{job_id}/apply", status_code=202)
def apply_to_job(job_id: int, services: ServicesDep) -> JSONResponse:
    """Starts tailoring my resume for the job (202), or returns the job's open application (200)."""
    application, created = services.applications.apply(job_id)
    body = application_json(application, services.jobs.get(job_id))
    return JSONResponse(body, status_code=202 if created else 200)


@router.get("/applications/{application_id}")
def get_application(application_id: int, services: ServicesDep) -> dict[str, Any]:
    application = services.applications.get(application_id)
    return application_json(application, services.jobs.get(application.job_id))


@router.put("/applications/{application_id}/resume")
def edit_tailored_resume(application_id: int, body: TailoredResumeIn, services: ServicesDep) -> dict[str, Any]:
    """Regenerates the tailored .docx and PDF from my edits."""
    application = services.applications.edit(application_id, body.summary, body.skills)
    return application_json(application, services.jobs.get(application.job_id))


@router.delete("/applications/{application_id}", status_code=204)
def cancel_application(application_id: int, services: ServicesDep) -> Response:
    services.applications.cancel(application_id)
    return Response(status_code=204)


@router.get("/applications/{application_id}/resume.pdf")
def get_tailored_pdf(application_id: int, services: ServicesDep) -> FileResponse:
    return FileResponse(services.applications.file(application_id, TAILORED_PDF), media_type="application/pdf")


@router.get("/applications/{application_id}/resume.docx")
def get_tailored_docx(application_id: int, services: ServicesDep) -> FileResponse:
    application = services.applications.get(application_id)
    company = services.jobs.get(application.job_id).posting.board_id
    return FileResponse(
        services.applications.file(application_id, TAILORED_DOCX),
        media_type=DOCX_TYPE,
        filename=f"Resume - {company}.docx",
    )
