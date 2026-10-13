from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Response

from job_tracker.routes.dependencies import ServicesDep
from job_tracker.validators.answers import BankEntryIn

router = APIRouter(prefix="/api/answer-bank", tags=["answer bank"])


@router.get("")
def list_answers(services: ServicesDep) -> list[dict[str, Any]]:
    return [asdict(entry) for entry in services.answer_bank.list()]


@router.post("", status_code=201)
def add_answer(body: BankEntryIn, services: ServicesDep) -> dict[str, Any]:
    return asdict(services.answer_bank.create(body.question, body.answer, body.category))


@router.put("/{entry_id}")
def update_answer(entry_id: int, body: BankEntryIn, services: ServicesDep) -> dict[str, Any]:
    return asdict(services.answer_bank.update(entry_id, body.question, body.answer, body.category))


@router.delete("/{entry_id}", status_code=204)
def delete_answer(entry_id: int, services: ServicesDep) -> Response:
    services.answer_bank.delete(entry_id)
    return Response(status_code=204)
