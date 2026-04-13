"""SQLAlchemy UnitOfWork для транзакционных use-case."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.db.sqlalchemy.session_context import (
    reset_current_session,
    set_current_session,
)


class SqlAlchemyUnitOfWork:
    """UnitOfWork с единой SQL-сессией на use-case."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._token: object | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self._token = set_current_session(self._session)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        try:
            if self._session is not None and exc is not None:
                self._session.rollback()
        finally:
            if self._token is not None:
                reset_current_session(self._token)
            if self._session is not None:
                self._session.close()
            self._session = None
            self._token = None

    def commit(self) -> None:
        """Фиксирует транзакцию."""

        if self._session is None:
            return
        self._session.commit()

    def rollback(self) -> None:
        """Откатывает транзакцию."""

        if self._session is None:
            return
        self._session.rollback()
