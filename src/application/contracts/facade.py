"""Контракт фасада application-слоя payments_service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .commands import (
    ApprovePaymentIntentCommand,
    CancelPaymentIntentCommand,
    CreatePaymentIntentCommand,
    RejectPaymentIntentCommand,
)
from .queries import (
    GetCourseAccessGrantQuery,
    GetPaymentIntentQuery,
    ListPaymentsByParentQuery,
)


@dataclass(frozen=True, slots=True)
class PaymentIntentView:
    """Read-модель PaymentIntent для interface-слоя."""

    payment_intent_id: str
    parent_id: str
    student_id: str
    course_id: str
    status: str
    base_price: float
    final_price: float
    currency: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class CourseAccessGrantView:
    """Read-модель доступа к курсу."""

    access_grant_id: str
    payment_intent_id: str
    course_id: str
    student_id: str
    status: str
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int


class ApplicationFacade(Protocol):
    """Единая точка входа для interface-слоя."""

    def create_payment_intent(
        self, command: CreatePaymentIntentCommand
    ) -> PaymentIntentView:
        """Создает intent на оплату."""

    def approve_payment_intent(
        self, command: ApprovePaymentIntentCommand
    ) -> CourseAccessGrantView:
        """Подтверждает оплату и активирует доступ."""

    def reject_payment_intent(
        self, command: RejectPaymentIntentCommand
    ) -> PaymentIntentView:
        """Отклоняет оплату."""

    def cancel_payment_intent(
        self, command: CancelPaymentIntentCommand
    ) -> PaymentIntentView:
        """Отменяет intent владельцем-parent."""

    def get_payment_intent(self, query: GetPaymentIntentQuery) -> PaymentIntentView:
        """Возвращает intent по id."""

    def get_course_access_grant(
        self, query: GetCourseAccessGrantQuery
    ) -> CourseAccessGrantView:
        """Возвращает доступ к курсу по id."""

    def list_payments_by_parent(
        self, query: ListPaymentsByParentQuery
    ) -> list[PaymentIntentView]:
        """Возвращает платежи родителя."""
