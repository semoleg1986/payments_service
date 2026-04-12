"""Репозиторий агрегата PaymentIntent."""

from __future__ import annotations

from typing import Protocol

from .entity import PaymentIntent


class PaymentIntentRepository(Protocol):
    """Контракт репозитория заявок на оплату."""

    def get(self, payment_intent_id: str) -> PaymentIntent | None:
        """Возвращает intent по id или None."""

    def get_by_idempotency_key(
        self, parent_id: str, idempotency_key: str
    ) -> PaymentIntent | None:
        """Возвращает intent по parent+idempotency_key или None."""

    def save(self, intent: PaymentIntent) -> None:
        """Сохраняет агрегат PaymentIntent."""
