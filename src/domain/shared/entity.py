"""Общие технические метаданные сущностей/агрегатов."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class EntityMeta:
    """Единые технические метаданные доменной сущности/агрегата."""

    version: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    archived_at: datetime | None = None
    archived_by: str | None = None

    @classmethod
    def create(cls, at: datetime, actor_id: str) -> "EntityMeta":
        """Создает начальные метаданные."""

        return cls(
            version=1,
            created_at=at,
            created_by=actor_id,
            updated_at=at,
            updated_by=actor_id,
        )

    def touch(self, at: datetime, actor_id: str) -> None:
        """Фиксирует изменение и увеличивает версию."""

        self.version += 1
        self.updated_at = at
        self.updated_by = actor_id

    def mark_archived(self, at: datetime, actor_id: str) -> None:
        """Фиксирует архивирование сущности."""

        self.archived_at = at
        self.archived_by = actor_id
        self.touch(at=at, actor_id=actor_id)
