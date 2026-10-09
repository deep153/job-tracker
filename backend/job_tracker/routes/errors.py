from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from job_tracker.services.errors import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    ServiceError,
    SetupIncompleteError,
    TooLargeError,
)

_STATUS: list[tuple[type[ServiceError], int]] = [
    (NotFoundError, 404),
    (InvalidRequestError, 422),
    (ConflictError, 409),
    (TooLargeError, 413),
    (SetupIncompleteError, 400),
]


def _service_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, ServiceError)
    status = next((code for kind, code in _STATUS if isinstance(error, kind)), 400)
    return JSONResponse(status_code=status, content={"detail": error.message})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, _service_error)
