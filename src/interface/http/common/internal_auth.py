"""Проверка сервисного токена для internal endpoint-ов."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from src.infrastructure.config.settings import Settings
from src.interface.http.wiring import get_settings


def require_service_token(
    settings: Settings = Depends(get_settings),
    x_service_token: str | None = Header(default=None),
) -> None:
    """Проверяет внутренний токен вызова сервиса."""

    if not x_service_token or x_service_token != settings.service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный service token.",
        )
