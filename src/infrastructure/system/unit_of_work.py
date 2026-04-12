"""In-memory реализация UnitOfWork."""

from __future__ import annotations


class InMemoryUnitOfWork:
    """No-op UnitOfWork для in-memory режима."""

    def __enter__(self) -> "InMemoryUnitOfWork":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc is not None:
            self.rollback()

    def commit(self) -> None:
        """No-op commit."""

    def rollback(self) -> None:
        """No-op rollback."""
