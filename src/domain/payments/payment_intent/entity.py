"""Aggregate Root заявки на оплату."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.errors import InvariantViolationError
from src.domain.shared.entity import EntityMeta
from src.domain.shared.statuses import PaymentStatus

from .events import PaymentIntentApproved, PaymentIntentCreated, PaymentIntentRejected
from .value_objects import Discount, Money, PaymentContext


@dataclass(slots=True)
class PaymentIntent:
    """Aggregate Root заявки на оплату курса."""

    payment_intent_id: str
    context: PaymentContext
    base_price: Money
    discount: Discount
    final_price: Money
    status: PaymentStatus
    meta: EntityMeta
    rejected_reason: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejected_at: datetime | None = None
    rejected_by: str | None = None
    events: list[object] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        payment_intent_id: str,
        context: PaymentContext,
        base_price: Money,
        discount: Discount,
        created_at: datetime,
        created_by: str,
    ) -> "PaymentIntent":
        """Создает новую заявку на оплату."""

        if not payment_intent_id.strip():
            raise InvariantViolationError("payment_intent_id обязателен.")
        if created_by != context.parent_id:
            raise InvariantViolationError(
                "Создатель intent должен совпадать с parent_id."
            )

        final_price = discount.apply_to(base_price)
        entity = cls(
            payment_intent_id=payment_intent_id,
            context=context,
            base_price=base_price,
            discount=discount,
            final_price=final_price,
            status=PaymentStatus.PENDING,
            meta=EntityMeta.create(at=created_at, actor_id=created_by),
        )
        entity.events.append(
            PaymentIntentCreated(
                payment_intent_id=payment_intent_id,
                parent_id=context.parent_id,
                student_id=context.student_id,
                course_id=context.course_id,
                occurred_at=created_at,
            )
        )
        return entity

    def approve(self, admin_id: str, approved_at: datetime) -> None:
        """Подтверждает оплату и переводит заявку в approved."""

        if self.status != PaymentStatus.PENDING:
            raise InvariantViolationError("Подтвердить можно только pending intent.")
        self.status = PaymentStatus.APPROVED
        self.approved_at = approved_at
        self.approved_by = admin_id
        self.meta.touch(at=approved_at, actor_id=admin_id)
        self.events.append(
            PaymentIntentApproved(
                payment_intent_id=self.payment_intent_id,
                approved_by=admin_id,
                occurred_at=approved_at,
            )
        )

    def reject(
        self, admin_id: str, rejected_at: datetime, reason: str | None = None
    ) -> None:
        """Отклоняет заявку и переводит её в rejected."""

        if self.status != PaymentStatus.PENDING:
            raise InvariantViolationError("Отклонить можно только pending intent.")
        self.status = PaymentStatus.REJECTED
        self.rejected_reason = reason.strip() if reason else None
        self.rejected_at = rejected_at
        self.rejected_by = admin_id
        self.meta.touch(at=rejected_at, actor_id=admin_id)
        self.events.append(
            PaymentIntentRejected(
                payment_intent_id=self.payment_intent_id,
                rejected_by=admin_id,
                reason=self.rejected_reason,
                occurred_at=rejected_at,
            )
        )

    def cancel(self, actor_id: str, cancelled_at: datetime) -> None:
        """Отменяет заявку владельцем до решения администратора."""

        if self.status != PaymentStatus.PENDING:
            raise InvariantViolationError("Отменить можно только pending intent.")
        if actor_id != self.context.parent_id:
            raise InvariantViolationError(
                "Отменить intent может только владелец-parent."
            )
        self.status = PaymentStatus.CANCELLED
        self.meta.touch(at=cancelled_at, actor_id=actor_id)

    def expire(self, expired_at: datetime, changed_by: str) -> None:
        """Переводит intent в expired по TTL."""

        if self.status != PaymentStatus.PENDING:
            raise InvariantViolationError(
                "В expired можно перевести только pending intent."
            )
        self.status = PaymentStatus.EXPIRED
        self.meta.touch(at=expired_at, actor_id=changed_by)
