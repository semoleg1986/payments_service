"""Команды application-слоя payments_service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreatePaymentIntentCommand:
    """Команда создания заявки на оплату."""

    payment_intent_id: str
    parent_id: str
    student_id: str
    course_id: str
    attribution_token: str | None
    idempotency_key: str | None
    actor_id: str
    actor_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ApprovePaymentIntentCommand:
    """Команда подтверждения оплаты администратором."""

    payment_intent_id: str
    admin_id: str
    admin_roles: tuple[str, ...]
    access_grant_id: str


@dataclass(frozen=True, slots=True)
class RejectPaymentIntentCommand:
    """Команда отклонения оплаты администратором."""

    payment_intent_id: str
    admin_id: str
    admin_roles: tuple[str, ...]
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CancelPaymentIntentCommand:
    """Команда отмены заявки владельцем-parent."""

    payment_intent_id: str
    actor_id: str
    actor_roles: tuple[str, ...]
