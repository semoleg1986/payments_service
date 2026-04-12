"""Порты application-слоя payments_service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.domain.payments import CourseAccessGrant, PaymentIntent


class UnitOfWork(Protocol):
    """Транзакционный порт Unit of Work."""

    def __enter__(self) -> "UnitOfWork":
        """Начинает транзакционный блок."""

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Завершает транзакционный блок."""

    def commit(self) -> None:
        """Фиксирует транзакцию."""

    def rollback(self) -> None:
        """Откатывает транзакцию."""


class Clock(Protocol):
    """Порт источника времени."""

    def now(self) -> datetime:
        """Возвращает текущее UTC-время."""


class IdGenerator(Protocol):
    """Порт генератора идентификаторов."""

    def new_id(self) -> str:
        """Возвращает новый идентификатор."""


class PaymentIntentRepositoryPort(Protocol):
    """Порт репозитория PaymentIntent."""

    def get(self, payment_intent_id: str) -> PaymentIntent | None:
        """Возвращает intent по id или None."""

    def get_by_idempotency_key(
        self, parent_id: str, idempotency_key: str
    ) -> PaymentIntent | None:
        """Возвращает intent по parent+idempotency_key или None."""

    def save(self, intent: PaymentIntent) -> None:
        """Сохраняет intent."""


class CourseAccessGrantRepositoryPort(Protocol):
    """Порт репозитория CourseAccessGrant."""

    def get(self, access_grant_id: str) -> CourseAccessGrant | None:
        """Возвращает access grant по id или None."""

    def get_by_payment_intent(self, payment_intent_id: str) -> CourseAccessGrant | None:
        """Возвращает access grant по payment_intent_id или None."""

    def exists_active_by_course_and_student(
        self, course_id: str, student_id: str
    ) -> bool:
        """Проверяет наличие active-доступа по course/student."""

    def save(self, access_grant: CourseAccessGrant) -> None:
        """Сохраняет access grant."""


@dataclass(frozen=True, slots=True)
class CourseSnapshot:
    """Минимальный снимок курса для расчета оплаты."""

    course_id: str
    price: float
    currency: str
    access_ttl_days: int | None


class CourseCatalogPort(Protocol):
    """Порт чтения данных курса."""

    def get_course(self, course_id: str) -> CourseSnapshot | None:
        """Возвращает данные курса по id или None."""


class UserRelationsPort(Protocol):
    """Порт проверки связей parent->student."""

    def is_parent_of_student(self, parent_id: str, student_id: str) -> bool:
        """Проверяет связь родителя и ученика."""


@dataclass(frozen=True, slots=True)
class DiscountSnapshot:
    """Минимальный снимок скидки от attribution-service."""

    kind: str
    value: float


class AttributionDiscountPort(Protocol):
    """Порт получения скидки по токену атрибуции."""

    def resolve_discount(
        self,
        attribution_token: str | None,
        course_id: str,
        parent_id: str,
    ) -> DiscountSnapshot:
        """Возвращает скидку для расчета final_price."""
