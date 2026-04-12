"""Системные реализации генератора идентификаторов."""

from __future__ import annotations

import uuid


class UuidGenerator:
    """Генератор UUID4."""

    def new_id(self) -> str:
        return str(uuid.uuid4())
