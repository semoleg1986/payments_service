"""Value Objects агрегата PaymentIntent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from src.domain.errors import InvariantViolationError

_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Money:
    """Денежная сумма в ISO-валюте."""

    amount: float
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvariantViolationError("Сумма не может быть отрицательной.")
        if not _CURRENCY_PATTERN.fullmatch(self.currency):
            raise InvariantViolationError(
                "currency должен быть ISO-4217 (3 заглавные буквы)."
            )


@dataclass(frozen=True, slots=True)
class Discount:
    """Скидка на оплату курса."""

    kind: str  # none|percent|fixed
    value: float

    def __post_init__(self) -> None:
        if self.kind not in {"none", "percent", "fixed"}:
            raise InvariantViolationError("kind скидки должен быть none|percent|fixed.")
        if self.value < 0:
            raise InvariantViolationError(
                "Значение скидки не может быть отрицательным."
            )
        if self.kind == "percent" and self.value > 100:
            raise InvariantViolationError("Процент скидки не может быть больше 100.")
        if self.kind == "none" and self.value != 0:
            raise InvariantViolationError("Для none скидка должна быть 0.")

    def apply_to(self, base: Money) -> Money:
        """Применяет скидку к базовой цене."""

        if self.kind == "none":
            final_amount = base.amount
        elif self.kind == "percent":
            final_amount = base.amount * (1 - self.value / 100)
        else:
            final_amount = max(base.amount - self.value, 0.0)
        return Money(amount=round(final_amount, 2), currency=base.currency)


@dataclass(frozen=True, slots=True)
class PaymentContext:
    """Бизнес-контекст заявки на оплату."""

    parent_id: str
    student_id: str
    course_id: str
    attribution_token: str | None = None
    idempotency_key: str | None = None
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.parent_id.strip():
            raise InvariantViolationError("parent_id обязателен.")
        if not self.student_id.strip():
            raise InvariantViolationError("student_id обязателен.")
        if not self.course_id.strip():
            raise InvariantViolationError("course_id обязателен.")
        if self.idempotency_key is not None and not self.idempotency_key.strip():
            raise InvariantViolationError("idempotency_key не может быть пустым.")
