"""Системные реализации порта времени."""

from __future__ import annotations

from datetime import UTC, datetime


class UtcClock:
    """Часы UTC для application-слоя."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)
