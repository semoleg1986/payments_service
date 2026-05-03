"""Observability-инструменты HTTP-слоя."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from contextvars import ContextVar
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import PlainTextResponse, Response

_LOGGER = logging.getLogger("payments_service.http")
_SERVICE = "payments_service"
_METRICS_LOCK = Lock()
_REQUESTS_TOTAL: dict[tuple[str, str, str, str], int] = defaultdict(int)
_REQUEST_DURATION_SUM: dict[tuple[str, str, str], float] = defaultdict(float)
_REQUEST_DURATION_COUNT: dict[tuple[str, str, str], int] = defaultdict(int)
_ERRORS_TOTAL: dict[tuple[str, str, str], int] = defaultdict(int)
_CUSTOM_COUNTER_DOCS: dict[str, str] = {}
_CUSTOM_COUNTER_LABELS: dict[str, tuple[str, ...]] = {}
_CUSTOM_COUNTER_VALUES: dict[str, dict[tuple[str, ...], int]] = defaultdict(
    lambda: defaultdict(int)
)
_CURRENT_REQUEST_ID: ContextVar[str | None] = ContextVar(
    "payments_request_id", default=None
)
_CURRENT_CORRELATION_ID: ContextVar[str | None] = ContextVar(
    "payments_correlation_id", default=None
)


def configure_http_logging() -> None:
    """Включает лаконичное JSON-логирование для HTTP-событий."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def increment_counter(
    name: str,
    description: str,
    **labels: str,
) -> None:
    """Увеличивает кастомный counter с фиксированным набором labels."""

    label_names = tuple(sorted(labels))
    label_values = tuple(labels[label] for label in label_names)

    with _METRICS_LOCK:
        existing_description = _CUSTOM_COUNTER_DOCS.get(name)
        existing_labels = _CUSTOM_COUNTER_LABELS.get(name)
        if existing_description is None:
            _CUSTOM_COUNTER_DOCS[name] = description
            _CUSTOM_COUNTER_LABELS[name] = label_names
        elif existing_description != description or existing_labels != label_names:
            raise ValueError(f"Metric {name} already registered with different schema.")
        _CUSTOM_COUNTER_VALUES[name][label_values] += 1


def reset_metrics() -> None:
    """Сбрасывает накопленные метрики. Используется в тестах."""

    with _METRICS_LOCK:
        _REQUESTS_TOTAL.clear()
        _REQUEST_DURATION_SUM.clear()
        _REQUEST_DURATION_COUNT.clear()
        _ERRORS_TOTAL.clear()
        _CUSTOM_COUNTER_DOCS.clear()
        _CUSTOM_COUNTER_LABELS.clear()
        _CUSTOM_COUNTER_VALUES.clear()


def current_request_id() -> str | None:
    """Возвращает request_id текущего HTTP-контекста."""

    return _CURRENT_REQUEST_ID.get()


def current_correlation_id() -> str | None:
    """Возвращает correlation_id текущего HTTP-контекста."""

    return _CURRENT_CORRELATION_ID.get()


class _StructuredHttpLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request_token = _CURRENT_REQUEST_ID.set(request_id)
        correlation_token = _CURRENT_CORRELATION_ID.set(correlation_id)
        started_at = time.perf_counter()
        status_code = 500
        path = request.url.path

        try:
            response = await call_next(request)
            status_code = response.status_code
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            duration_seconds = time.perf_counter() - started_at
            duration_ms = round(duration_seconds * 1000, 2)
            status = str(status_code)

            with _METRICS_LOCK:
                _REQUESTS_TOTAL[(_SERVICE, request.method, path, status)] += 1
                _REQUEST_DURATION_SUM[
                    (_SERVICE, request.method, path)
                ] += duration_seconds
                _REQUEST_DURATION_COUNT[(_SERVICE, request.method, path)] += 1
                if status_code >= 400:
                    _ERRORS_TOTAL[(_SERVICE, path, status)] += 1

            event = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "service": _SERVICE,
                "event": "http_request",
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "path": path,
                "query": request.url.query,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
            _LOGGER.info(json.dumps(event, ensure_ascii=False))
            _CURRENT_REQUEST_ID.reset(request_token)
            _CURRENT_CORRELATION_ID.reset(correlation_token)


def install_observability(app: FastAPI) -> None:
    """Устанавливает middleware для request-id/metrics и structured logs."""

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        lines = [
            "# HELP http_requests_total Total HTTP requests.",
            "# TYPE http_requests_total counter",
        ]
        with _METRICS_LOCK:
            for (service, method, path, status), value in sorted(
                _REQUESTS_TOTAL.items()
            ):
                lines.append(
                    f'http_requests_total{{service="{service}",method="{method}",path="{path}",status="{status}"}} {value}'
                )
            lines.extend(
                [
                    "# HELP http_request_duration_seconds HTTP request latency in seconds.",
                    "# TYPE http_request_duration_seconds summary",
                ]
            )
            for (service, method, path), duration_sum in sorted(
                _REQUEST_DURATION_SUM.items()
            ):
                count = _REQUEST_DURATION_COUNT[(service, method, path)]
                labels = f'service="{service}",method="{method}",path="{path}"'
                lines.append(
                    f"http_request_duration_seconds_sum{{{labels}}} {duration_sum}"
                )
                lines.append(f"http_request_duration_seconds_count{{{labels}}} {count}")
            lines.extend(
                [
                    "# HELP http_errors_total Total HTTP error responses (status >= 400).",
                    "# TYPE http_errors_total counter",
                ]
            )
            for (service, path, status), value in sorted(_ERRORS_TOTAL.items()):
                lines.append(
                    f'http_errors_total{{service="{service}",path="{path}",status="{status}"}} {value}'
                )
            for name in sorted(_CUSTOM_COUNTER_DOCS):
                lines.extend(
                    [
                        f"# HELP {name} {_CUSTOM_COUNTER_DOCS[name]}",
                        f"# TYPE {name} counter",
                    ]
                )
                label_names = _CUSTOM_COUNTER_LABELS[name]
                for label_values, value in sorted(_CUSTOM_COUNTER_VALUES[name].items()):
                    if label_names:
                        labels = ",".join(
                            f'{label_name}="{label_value}"'
                            for label_name, label_value in zip(
                                label_names, label_values, strict=True
                            )
                        )
                        lines.append(f"{name}{{{labels}}} {value}")
                    else:
                        lines.append(f"{name} {value}")

        return PlainTextResponse(
            content="\n".join(lines) + "\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    app.add_middleware(_StructuredHttpLogMiddleware)
