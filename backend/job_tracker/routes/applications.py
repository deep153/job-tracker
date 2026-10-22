from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, JSONResponse

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.routes.resume import DOCX_TYPE
from job_tracker.serializers.applications import application_json, application_summary_json
from job_tracker.services.application_service import TAILORED_DOCX, TAILORED_PDF
from job_tracker.validators.answers import FormAnswersIn, SaveToBankIn
from job_tracker.validators.applications import CoverLetterIn, StatusIn, TailoredResumeIn

router = APIRouter(prefix="/api", tags=["applications"])


@router.post("/jobs/{job_id}/apply", status_code=202)
def apply_to_job(job_id: int, services: ServicesDep) -> JSONResponse:
    """Starts tailoring my resume for the job (202), or returns the job's open application (200)."""
    application, created = services.applications.apply(job_id)
    body = application_json(application, services.jobs.get(job_id))
    return JSONResponse(body, status_code=202 if created else 200)


@router.get("/applications")
def list_applications(services: ServicesDep) -> list[dict[str, Any]]:
    """Every application, newest first."""
    return [application_summary_json(application, job) for application, job in services.applications.list_all()]


@router.put("/applications/{application_id}/status")
def track_application(application_id: int, body: StatusIn, services: ServicesDep) -> dict[str, Any]:
    """Sets the status by hand after submitting (409 before). `submitted` marks one I finished in the browser."""
    application = services.applications.track(application_id, body.status)
    return application_json(application, services.jobs.get(application.job_id))


@router.get("/applications/{application_id}")
def get_application(application_id: int, services: ServicesDep) -> dict[str, Any]:
    application = services.applications.get(application_id)
    return application_json(application, services.jobs.get(application.job_id))


@router.put("/applications/{application_id}/resume")
def edit_tailored_resume(application_id: int, body: TailoredResumeIn, services: ServicesDep) -> dict[str, Any]:
    """Regenerates the tailored .docx and PDF from my edits."""
    bullets = {bullet.index: bullet.text for bullet in body.bullets}
    application = services.applications.edit(application_id, body.summary, body.skills, bullets)
    return application_json(application, services.jobs.get(application.job_id))


@router.put("/applications/{application_id}/cover-letter")
def edit_cover_letter(application_id: int, body: CoverLetterIn, services: ServicesDep) -> dict[str, Any]:
    application = services.applications.edit_cover_letter(application_id, body.text)
    return application_json(application, services.jobs.get(application.job_id))


@router.put("/applications/{application_id}/answers")
def answer_questions(application_id: int, body: FormAnswersIn, services: ServicesDep) -> dict[str, Any]:
    application = services.applications.answer(application_id, body.answers)
    return application_json(application, services.jobs.get(application.job_id))


@router.post("/applications/{application_id}/answers/save-to-bank")
def save_answer_to_bank(application_id: int, body: SaveToBankIn, services: ServicesDep) -> dict[str, Any]:
    """Saves the question's current answer into my answer bank (replacing my saved answer to the same question),
    so later applications are answered with it."""
    application = services.applications.save_to_bank(application_id, body.key)
    return application_json(application, services.jobs.get(application.job_id))


@router.post("/applications/{application_id}/approve")
def approve_application(application_id: int, services: ServicesDep) -> dict[str, Any]:
    """Starts sending the application (it's `submitting` until that ends). Refused (409) while anything still
    needs fixing, such as a required question with no answer, or once it's been sent."""
    application = services.applications.approve(application_id)
    return application_json(application, services.jobs.get(application.job_id))


@router.delete("/applications/{application_id}", status_code=204)
def cancel_application(application_id: int, services: ServicesDep) -> Response:
    services.applications.cancel(application_id)
    return Response(status_code=204)


@router.get("/applications/{application_id}/resume.pdf")
def get_tailored_pdf(application_id: int, services: ServicesDep) -> FileResponse:
    return FileResponse(services.applications.file(application_id, TAILORED_PDF), media_type="application/pdf")


@router.get("/applications/{application_id}/cover-letter.pdf")
def get_cover_letter_pdf(application_id: int, services: ServicesDep) -> FileResponse:
    """The cover letter as it's uploaded, when the form takes it as a file."""
    return FileResponse(services.applications.cover_letter_pdf(application_id), media_type="application/pdf")


@router.get("/applications/{application_id}/screenshot.png")
def get_screenshot(application_id: int, services: ServicesDep) -> FileResponse:
    """The page as it was when sending the application failed."""
    return FileResponse(services.applications.screenshot(application_id), media_type="image/png")


@router.get("/applications/{application_id}/resume.docx")
def get_tailored_docx(application_id: int, services: ServicesDep) -> FileResponse:
    application = services.applications.get(application_id)
    company = services.jobs.get(application.job_id).posting.board_id
    return FileResponse(
        services.applications.file(application_id, TAILORED_DOCX),
        media_type=DOCX_TYPE,
        filename=f"Resume - {company}.docx",
    )
