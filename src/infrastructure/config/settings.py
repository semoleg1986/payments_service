"""Конфигурация payments_service из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime-настройки сервиса."""

    app_name: str
    app_host: str
    app_port: int
    database_url: str
    use_inmemory: bool
    auto_create_schema: bool
    auth_jwks_url: str
    auth_jwks_json: str | None
    auth_issuer: str
    auth_audience: str
    service_token: str
    default_currency: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("PAYMENTS_APP_NAME", "payments_service"),
            app_host=os.getenv("PAYMENTS_APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("PAYMENTS_APP_PORT", "8004")),
            database_url=os.getenv(
                "PAYMENTS_DATABASE_URL",
                "sqlite:///./payments_service.db",
            ),
            use_inmemory=os.getenv("PAYMENTS_USE_INMEMORY", "1") == "1",
            auto_create_schema=os.getenv("PAYMENTS_AUTO_CREATE_SCHEMA", "0") == "1",
            auth_jwks_url=os.getenv(
                "PAYMENTS_AUTH_JWKS_URL",
                "http://localhost:8000/.well-known/jwks.json",
            ),
            auth_jwks_json=os.getenv("PAYMENTS_AUTH_JWKS_JSON"),
            auth_issuer=os.getenv("PAYMENTS_AUTH_ISSUER", "auth_service"),
            auth_audience=os.getenv("PAYMENTS_AUTH_AUDIENCE", "platform_clients"),
            service_token=os.getenv("PAYMENTS_SERVICE_TOKEN", "dev-service-token"),
            default_currency=os.getenv("PAYMENTS_DEFAULT_CURRENCY", "USD"),
        )
