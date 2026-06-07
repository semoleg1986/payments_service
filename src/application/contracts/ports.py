"""Порты application-слоя payments_service."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Callable, Protocol

from src.domain.payments import CourseAccessGrant, PaymentIntent


@dataclass(frozen=True, slots=True)
class AuditEvidenceRecord:
    """Append-only запись retained audit evidence."""

    audit_id: str
    action: str
    occurred_at: datetime
    result: str
    actor_id: str | None
    actor_roles: tuple[str, ...]
    target_type: str
    target_id: str | None
    reason: str | None = None
    reason_code: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    payment_intent_id: str | None = None


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


UnitOfWorkFactory = Callable[[], UnitOfWork]


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

    def list_by_parent(self, parent_id: str) -> list[PaymentIntent]:
        """Возвращает платежи родителя."""

    def list(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PaymentIntent]:
        """Возвращает список intent-ов с фильтрацией для admin read-side."""

    def get_latest_by_parent_student_course(
        self,
        *,
        parent_id: str,
        student_id: str,
        course_id: str,
    ) -> PaymentIntent | None:
        """Возвращает последний intent для parent/student/course."""

    def list_pending_by_student_and_course(
        self,
        *,
        student_id: str,
        course_id: str,
    ) -> list[PaymentIntent]:
        """Возвращает pending intents для student/course."""


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

    def find_by_course_and_student(
        self,
        course_id: str,
        student_id: str,
    ) -> CourseAccessGrant | None:
        """Возвращает доступ для пары course/student."""

    def get_active_by_student_and_course(
        self,
        *,
        course_id: str,
        student_id: str,
    ) -> CourseAccessGrant | None:
        """Возвращает active доступ для пары course/student."""

    def save(self, access_grant: CourseAccessGrant) -> None:
        """Сохраняет access grant."""


@dataclass(frozen=True, slots=True)
class CourseSnapshot:
    """Минимальный снимок курса для расчета оплаты."""

    course_id: str
    access_ttl_days: int | None


class CourseCatalogPort(Protocol):
    """Порт чтения данных курса."""

    def get_course(self, course_id: str) -> CourseSnapshot | None:
        """Возвращает данные курса по id или None."""


@dataclass(frozen=True, slots=True)
class OfferSnapshot:
    """Минимальный коммерческий снимок offer для checkout."""

    offer_id: str
    course_id: str
    price: float
    currency: str


class CommercialCatalogPort(Protocol):
    """Порт чтения коммерческих offer из commercial_catalog_service."""

    def get_offer(self, offer_id: str) -> OfferSnapshot | None:
        """Возвращает offer snapshot по id или None."""


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


@dataclass(frozen=True, slots=True)
class BonusQuoteSnapshot:
    """Минимальный снимок разрешенного бонусного списания."""

    requested_amount: int
    allowed_amount: int


class BonusWalletPort(Protocol):
    """Порт бонусного кошелька для quote/commit/revert."""

    def quote_redeem(
        self,
        *,
        parent_id: str,
        requested_amount: int,
        payment_intent_id: str,
    ) -> BonusQuoteSnapshot:
        """Возвращает допустимое бонусное списание без сайд-эффекта."""

    def commit_redeem(
        self,
        *,
        parent_id: str,
        amount: int,
        payment_intent_id: str,
        idempotency_key: str,
    ) -> None:
        """Фиксирует бонусное списание для платежа."""

    def revert_redeem(
        self,
        *,
        parent_id: str,
        amount: int,
        payment_intent_id: str,
        idempotency_key: str,
    ) -> None:
        """Компенсирует ранее зафиксированное бонусное списание."""


class OutboxEventStatus(StrEnum):
    """Статус доставки outbox-события."""

    PENDING = "pending"
    PROCESSED = "processed"


class OutboxEventType(StrEnum):
    """Типы межсервисных side effect событий payments_service."""

    COURSE_ACCESS_GRANTED_SYNC = "course_access_granted_sync"
    BONUS_REDEEM_COMMIT = "bonus_redeem_commit"


@dataclass(frozen=True, slots=True)
class OutboxEventRecord:
    """Persisted outbox event для надежной межсервисной доставки."""

    event_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: OutboxEventType
    payload_json: str
    status: OutboxEventStatus
    attempt_count: int
    available_at: datetime
    created_at: datetime
    processed_at: datetime | None = None
    last_error: str | None = None

    def mark_processed(self, *, at: datetime) -> "OutboxEventRecord":
        """Возвращает событие в состоянии processed."""

        return replace(
            self,
            status=OutboxEventStatus.PROCESSED,
            processed_at=at,
            last_error=None,
        )

    def mark_failed(self, *, error: str) -> "OutboxEventRecord":
        """Возвращает событие с увеличенным счетчиком попыток."""

        return replace(
            self,
            attempt_count=self.attempt_count + 1,
            last_error=error[:1000],
        )


class OutboxEventRepositoryPort(Protocol):
    """Порт persisted outbox-хранилища."""

    def add(self, event: OutboxEventRecord) -> None:
        """Добавляет новое событие в outbox."""

    def save(self, event: OutboxEventRecord) -> None:
        """Обновляет состояние существующего outbox-события."""

    def list_pending(self, *, limit: int = 100) -> list[OutboxEventRecord]:
        """Возвращает pending-события в порядке создания."""

    def list_pending_by_aggregate(
        self, *, aggregate_id: str
    ) -> list[OutboxEventRecord]:
        """Возвращает pending-события для конкретного aggregate."""

    def count_pending(self) -> int:
        """Возвращает количество pending-событий."""

    def oldest_pending_created_at(self) -> datetime | None:
        """Возвращает created_at самого старого pending-события."""


class CourseAccessSyncPort(Protocol):
    """Порт синхронизации access grant в course_service."""

    def sync_course_access_granted(
        self,
        *,
        event_id: str,
        course_id: str,
        student_id: str,
        granted_status: str,
    ) -> None:
        """Отправляет событие course.access.granted в course_service."""


class AccessTokenVerifier(Protocol):
    """Порт верификатора access token."""

    def decode_access(self, access_token: str) -> dict[str, str | list[str]]:
        """Декодирует access token и возвращает claims."""


class AuditEvidenceRepositoryPort(Protocol):
    """Порт append-only хранения audit evidence."""

    def append(self, record: AuditEvidenceRecord) -> None:
        """Сохраняет audit evidence запись."""
