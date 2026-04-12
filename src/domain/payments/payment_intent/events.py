"""Доменные события агрегата PaymentIntent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PaymentIntentCreated:
    """Событие создания заявки на оплату."""

    payment_intent_id: str
    parent_id: str
    student_id: str
    course_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PaymentIntentApproved:
    """Событие подтверждения оплаты."""

    payment_intent_id: str
    approved_by: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class PaymentIntentRejected:
    """Событие отклонения оплаты."""

    payment_intent_id: str
    rejected_by: str
    reason: str | None
    occurred_at: datetime
