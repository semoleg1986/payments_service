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
    GetCheckoutStateQuery,
    GetCourseAccessGrantQuery,
    GetPaymentIntentQuery,
    ListPaymentIntentsQuery,
    ListPaymentsByParentQuery,
)


@dataclass(frozen=True, slots=True)
class PaymentIntentView:
    """Read-модель PaymentIntent для interface-слоя."""

    payment_intent_id: str
    parent_id: str
    student_id: str
    offer_id: str
    course_id: str
    status: str
    base_price: float
    final_price: float
    bonus_amount: int
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
    offer_id: str
    course_id: str
    student_id: str
    status: str
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class AccessCheckView:
    """Read-модель проверки доступа ученика к курсу."""

    has_access: bool
    course_id: str
    student_id: str
    access_grant_id: str | None = None
    status: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CheckoutActionsView:
    """Разрешенные действия checkout UI."""

    can_create_payment_intent: bool
    can_retry_payment: bool
    next_action: str
    resume_payment_intent_id: str | None = None


@dataclass(frozen=True, slots=True)
class CheckoutOfferView:
    """Явный selected/purchased offer block для checkout-state."""

    offer_id: str
    course_id: str
    base_price: float
    final_price: float
    bonus_amount: int
    currency: str
    source: str
    payment_intent_id: str | None = None
    access_grant_id: str | None = None


@dataclass(frozen=True, slots=True)
class CheckoutStateView:
    """Read-модель checkout-state для parent UI."""

    parent_id: str
    student_id: str
    course_id: str
    checkout_state: str
    selected_offer: CheckoutOfferView | None
    purchased_offer: CheckoutOfferView | None
    latest_payment_intent: PaymentIntentView | None
    access_grant: CourseAccessGrantView | None
    available_actions: CheckoutActionsView


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

    def list_payment_intents(
        self, query: ListPaymentIntentsQuery
    ) -> list[PaymentIntentView]:
        """Возвращает список intent-ов для admin read-side."""

    def get_checkout_state(self, query: GetCheckoutStateQuery) -> CheckoutStateView:
        """Возвращает checkout-state для parent/student/course."""

    def check_course_access(self, course_id: str, student_id: str) -> AccessCheckView:
        """Проверяет активный доступ ученика к курсу."""
