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
    integrations_use_inmemory: bool
    commercial_catalog_service_base_url: str
    commercial_catalog_service_token: str
    commercial_catalog_service_timeout_seconds: float
    course_service_base_url: str
    course_service_token: str
    course_service_timeout_seconds: float
    users_service_base_url: str
    users_service_token: str
    users_service_timeout_seconds: float
    attr_service_base_url: str
    attr_service_token: str
    attr_service_timeout_seconds: float
    bonus_service_base_url: str
    bonus_service_token: str
    bonus_service_timeout_seconds: float
    parent_payment_create_rate_limit_max: int
    parent_payment_create_rate_limit_window_seconds: int
    admin_payment_approve_rate_limit_max: int
    admin_payment_approve_rate_limit_window_seconds: int

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
            integrations_use_inmemory=os.getenv(
                "PAYMENTS_INTEGRATIONS_USE_INMEMORY", "1"
            )
            == "1",
            commercial_catalog_service_base_url=os.getenv(
                "PAYMENTS_COMMERCIAL_CATALOG_SERVICE_BASE_URL",
                "http://localhost:8007",
            ),
            commercial_catalog_service_token=os.getenv(
                "PAYMENTS_COMMERCIAL_CATALOG_SERVICE_TOKEN",
                "dev-service-token",
            ),
            commercial_catalog_service_timeout_seconds=float(
                os.getenv("PAYMENTS_COMMERCIAL_CATALOG_SERVICE_TIMEOUT_SECONDS", "2")
            ),
            course_service_base_url=os.getenv(
                "PAYMENTS_COURSE_SERVICE_BASE_URL", "http://localhost:8001"
            ),
            course_service_token=os.getenv(
                "PAYMENTS_COURSE_SERVICE_TOKEN", "dev-service-token"
            ),
            course_service_timeout_seconds=float(
                os.getenv("PAYMENTS_COURSE_SERVICE_TIMEOUT_SECONDS", "2")
            ),
            users_service_base_url=os.getenv(
                "PAYMENTS_USERS_SERVICE_BASE_URL", "http://localhost:8002"
            ),
            users_service_token=os.getenv(
                "PAYMENTS_USERS_SERVICE_TOKEN", "dev-service-token"
            ),
            users_service_timeout_seconds=float(
                os.getenv("PAYMENTS_USERS_SERVICE_TIMEOUT_SECONDS", "2")
            ),
            attr_service_base_url=os.getenv(
                "PAYMENTS_ATTR_SERVICE_BASE_URL", "http://localhost:8003"
            ),
            attr_service_token=os.getenv(
                "PAYMENTS_ATTR_SERVICE_TOKEN", "dev-service-token"
            ),
            attr_service_timeout_seconds=float(
                os.getenv("PAYMENTS_ATTR_SERVICE_TIMEOUT_SECONDS", "2")
            ),
            bonus_service_base_url=os.getenv(
                "PAYMENTS_BONUS_SERVICE_BASE_URL", "http://localhost:8006"
            ),
            bonus_service_token=os.getenv(
                "PAYMENTS_BONUS_SERVICE_TOKEN", "dev-service-token"
            ),
            bonus_service_timeout_seconds=float(
                os.getenv("PAYMENTS_BONUS_SERVICE_TIMEOUT_SECONDS", "2")
            ),
            parent_payment_create_rate_limit_max=int(
                os.getenv("PAYMENTS_RATE_LIMIT_PARENT_CREATE_MAX", "20")
            ),
            parent_payment_create_rate_limit_window_seconds=int(
                os.getenv("PAYMENTS_RATE_LIMIT_PARENT_CREATE_WINDOW_SECONDS", "60")
            ),
            admin_payment_approve_rate_limit_max=int(
                os.getenv("PAYMENTS_RATE_LIMIT_ADMIN_APPROVE_MAX", "30")
            ),
            admin_payment_approve_rate_limit_window_seconds=int(
                os.getenv("PAYMENTS_RATE_LIMIT_ADMIN_APPROVE_WINDOW_SECONDS", "60")
            ),
        )
