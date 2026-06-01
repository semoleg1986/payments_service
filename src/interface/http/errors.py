"""Обработчики ошибок HTTP-слоя."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.domain.errors import AccessDeniedError, InvariantViolationError, NotFoundError
from src.interface.http.problem_types import (
    ACCESS_DENIED,
    CONFLICT,
    INTERNAL_ERROR,
    INVARIANT_VIOLATION,
    NOT_FOUND,
    UNAUTHORIZED,
    VALIDATION_ERROR,
)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


def _headers(request: Request) -> dict[str, str]:
    headers = {}
    request_id = _request_id(request)
    correlation_id = _correlation_id(request)
    if request_id is not None:
        headers["X-Request-ID"] = request_id
    if correlation_id is not None:
        headers["X-Correlation-ID"] = correlation_id
    return headers


def _headers_with_extra(
    request: Request,
    extra: dict[str, str] | None,
) -> dict[str, str]:
    return {**(extra or {}), **_headers(request)}


def _problem(
    request: Request,
    *,
    status: int,
    title: str,
    problem_type: str,
    detail: object,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": problem_type,
            "title": title,
            "status": status,
            "detail": detail,
            "instance": str(request.url.path),
            "request_id": _request_id(request),
            "correlation_id": _correlation_id(request),
        },
        headers=_headers_with_extra(request, headers),
        media_type="application/problem+json",
    )


def install_error_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений."""

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _problem(
            request,
            status=422,
            title="Ошибка валидации",
            problem_type=VALIDATION_ERROR,
            detail=str(exc),
        )

    @app.exception_handler(AccessDeniedError)
    async def handle_access_denied(
        request: Request,
        exc: AccessDeniedError,
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Доступ запрещен",
            problem_type=ACCESS_DENIED,
            detail=str(exc),
        )

    @app.exception_handler(NotFoundError)
    async def handle_not_found(
        request: Request,
        exc: NotFoundError,
    ) -> JSONResponse:
        return _problem(
            request,
            status=404,
            title="Сущность не найдена",
            problem_type=NOT_FOUND,
            detail=str(exc),
        )

    @app.exception_handler(InvariantViolationError)
    async def handle_invariant_violation(
        request: Request,
        exc: InvariantViolationError,
    ) -> JSONResponse:
        return _problem(
            request,
            status=400,
            title="Нарушение бизнес-инварианта",
            problem_type=INVARIANT_VIOLATION,
            detail=str(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        mapping = {
            401: ("Не авторизован", UNAUTHORIZED),
            403: ("Доступ запрещен", ACCESS_DENIED),
            404: ("Сущность не найдена", NOT_FOUND),
            409: ("Конфликт", CONFLICT),
            422: ("Ошибка валидации", VALIDATION_ERROR),
        }
        title, problem_type = mapping.get(
            exc.status_code, (str(exc.detail), "about:blank")
        )
        return _problem(
            request,
            status=exc.status_code,
            title=title,
            problem_type=problem_type,
            detail=exc.detail,
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return _problem(
            request,
            status=500,
            title="Внутренняя ошибка сервиса",
            problem_type=INTERNAL_ERROR,
            detail="Unhandled server error.",
        )
