"""Провайдеры runtime-зависимостей HTTP-слоя."""

from __future__ import annotations

from src.application.contracts import AccessTokenVerifier, ApplicationFacade
from src.infrastructure.config.settings import Settings
from src.infrastructure.di.composition import RuntimeContainer, build_runtime

_runtime: RuntimeContainer | None = None


def get_runtime() -> RuntimeContainer:
    """Возвращает singleton runtime-контейнер."""

    global _runtime  # noqa: PLW0603
    if _runtime is None:
        _runtime = build_runtime()
    return _runtime


def get_facade() -> ApplicationFacade:
    """Провайдер application facade."""

    return get_runtime().facade


def get_settings() -> Settings:
    """Провайдер runtime settings."""

    return get_runtime().settings


def get_access_token_verifier() -> AccessTokenVerifier:
    """Провайдер verifier access token."""

    return get_runtime().access_token_verifier
