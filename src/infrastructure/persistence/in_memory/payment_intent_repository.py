"""In-memory репозиторий PaymentIntent."""

from __future__ import annotations

from src.domain.payments.payment_intent.entity import PaymentIntent


class InMemoryPaymentIntentRepository:
    """Хранилище PaymentIntent в памяти процесса."""

    def __init__(self) -> None:
        self._items: dict[str, PaymentIntent] = {}

    def get(self, payment_intent_id: str) -> PaymentIntent | None:
        return self._items.get(payment_intent_id)

    def get_by_idempotency_key(
        self,
        parent_id: str,
        idempotency_key: str,
    ) -> PaymentIntent | None:
        for intent in self._items.values():
            if (
                intent.context.parent_id == parent_id
                and intent.context.idempotency_key == idempotency_key
            ):
                return intent
        return None

    def save(self, intent: PaymentIntent) -> None:
        self._items[intent.payment_intent_id] = intent

    def list_by_parent(self, parent_id: str) -> list[PaymentIntent]:
        return [x for x in self._items.values() if x.context.parent_id == parent_id]

    def list(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PaymentIntent]:
        items = list(self._items.values())
        if status is not None:
            items = [x for x in items if x.status.value == status]
        items.sort(key=lambda item: item.meta.created_at, reverse=True)
        return items[offset : offset + limit]

    def get_latest_by_parent_student_course(
        self,
        *,
        parent_id: str,
        student_id: str,
        course_id: str,
    ) -> PaymentIntent | None:
        items = [
            intent
            for intent in self._items.values()
            if intent.context.parent_id == parent_id
            and intent.context.student_id == student_id
            and intent.context.course_id == course_id
        ]
        if not items:
            return None
        items.sort(key=lambda item: item.meta.created_at, reverse=True)
        return items[0]
