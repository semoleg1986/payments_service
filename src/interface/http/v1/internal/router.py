"""Internal endpoint-ы платежного сервиса."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.application.contracts import ApplicationFacade
from src.interface.http.common.internal_auth import require_service_token
from src.interface.http.v1.schemas.access import AccessCheckResponse
from src.interface.http.wiring import get_facade

router = APIRouter(
    prefix="/internal/v1",
    tags=["internal-payments"],
    dependencies=[Depends(require_service_token)],
)


@router.get(
    "/access/{course_id}/{student_id}",
    response_model=AccessCheckResponse,
)
def check_course_access(
    course_id: str,
    student_id: str,
    facade: ApplicationFacade = Depends(get_facade),
) -> AccessCheckResponse:
    """Проверяет доступ ученика к курсу."""

    result = facade.check_course_access(course_id=course_id, student_id=student_id)
    return AccessCheckResponse.model_validate(result)
