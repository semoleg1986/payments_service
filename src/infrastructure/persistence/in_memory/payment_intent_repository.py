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
