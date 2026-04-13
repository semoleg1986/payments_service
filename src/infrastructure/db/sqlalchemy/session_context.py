"""Контекст текущей SQLAlchemy-сессии для UnitOfWork."""

from __future__ import annotations

from contextvars import ContextVar

from sqlalchemy.orm import Session

_CURRENT_SESSION: ContextVar[Session | None] = ContextVar(
    "payments_current_sqlalchemy_session",
    default=None,
)


def get_current_session() -> Session | None:
    """Возвращает текущую сессию UnitOfWork."""

    return _CURRENT_SESSION.get()


def set_current_session(session: Session | None) -> object:
    """Устанавливает текущую сессию и возвращает token для reset."""

    return _CURRENT_SESSION.set(session)


def reset_current_session(token: object) -> None:
    """Сбрасывает ContextVar к предыдущему состоянию."""

    _CURRENT_SESSION.reset(token)  # type: ignore[arg-type]
