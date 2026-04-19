"""Observability-инструменты HTTP-слоя."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

_LOGGER = logging.getLogger("payments_service.http")


def configure_http_logging() -> None:
    """Включает лаконичное JSON-логирование для HTTP-событий."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


class _StructuredHttpLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            event = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "service": "payments_service",
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
            _LOGGER.info(json.dumps(event, ensure_ascii=False))


def install_observability(app: FastAPI) -> None:
    """Устанавливает middleware для request-id и structured logs."""
    app.add_middleware(_StructuredHttpLogMiddleware)
