"""In-memory persisted outbox repository for payments_service."""

from __future__ import annotations

from src.application.contracts import OutboxEventRecord, OutboxEventStatus


class InMemoryPaymentOutboxRepository:
    """Простое in-memory хранилище outbox-событий для тестов."""

    def __init__(self) -> None:
        self._items: dict[str, OutboxEventRecord] = {}

    def add(self, event: OutboxEventRecord) -> None:
        self._items[event.event_id] = event

    def save(self, event: OutboxEventRecord) -> None:
        self._items[event.event_id] = event

    def list_pending(self, *, limit: int = 100) -> list[OutboxEventRecord]:
        return sorted(
            (
                item
                for item in self._items.values()
                if item.status == OutboxEventStatus.PENDING
            ),
            key=lambda item: item.created_at,
        )[:limit]

    def list_pending_by_aggregate(
        self, *, aggregate_id: str
    ) -> list[OutboxEventRecord]:
        return sorted(
            (
                item
                for item in self._items.values()
                if item.aggregate_id == aggregate_id
                and item.status == OutboxEventStatus.PENDING
            ),
            key=lambda item: item.created_at,
        )

    def count_pending(self) -> int:
        return sum(
            1
            for item in self._items.values()
            if item.status == OutboxEventStatus.PENDING
        )

    def oldest_pending_created_at(self):
        pending = [
            item.created_at
            for item in self._items.values()
            if item.status == OutboxEventStatus.PENDING
        ]
        return min(pending) if pending else None
