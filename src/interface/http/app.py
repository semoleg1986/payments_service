"""Сборка FastAPI-приложения payments_service."""

from __future__ import annotations

from fastapi import FastAPI

from src.interface.http.errors import install_error_handlers
from src.interface.http.health import router as health_router
from src.interface.http.v1.admin.router import router as admin_router
from src.interface.http.v1.internal.router import router as internal_router
from src.interface.http.v1.parent.router import router as parent_router


def create_app() -> FastAPI:
    """Создает и настраивает FastAPI app."""

    app = FastAPI(title="payments_service", version="0.1.0")
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(parent_router)
    app.include_router(admin_router)
    app.include_router(internal_router)
    return app
