"""Обработчики ошибок HTTP-слоя."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain.errors import AccessDeniedError, InvariantViolationError, NotFoundError
from src.interface.http.problem_types import (
    ACCESS_DENIED,
    INTERNAL_ERROR,
    INVARIANT_VIOLATION,
    NOT_FOUND,
    VALIDATION_ERROR,
)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def install_error_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений."""

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "type": VALIDATION_ERROR,
                "title": "Ошибка валидации",
                "status": 422,
                "detail": str(exc),
                "instance": str(request.url.path),
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(AccessDeniedError)
    async def handle_access_denied(
        request: Request,
        exc: AccessDeniedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "type": ACCESS_DENIED,
                "title": "Доступ запрещен",
                "status": 403,
                "detail": str(exc),
                "instance": str(request.url.path),
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(NotFoundError)
    async def handle_not_found(
        request: Request,
        exc: NotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "type": NOT_FOUND,
                "title": "Сущность не найдена",
                "status": 404,
                "detail": str(exc),
                "instance": str(request.url.path),
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(InvariantViolationError)
    async def handle_invariant_violation(
        request: Request,
        exc: InvariantViolationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "type": INVARIANT_VIOLATION,
                "title": "Нарушение бизнес-инварианта",
                "status": 400,
                "detail": str(exc),
                "instance": str(request.url.path),
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "type": INTERNAL_ERROR,
                "title": "Внутренняя ошибка сервиса",
                "status": 500,
                "detail": str(exc),
                "instance": str(request.url.path),
                "request_id": _request_id(request),
            },
        )
