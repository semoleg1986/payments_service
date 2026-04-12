"""Aggregate Root выдачи доступа к курсу."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.errors import InvariantViolationError
from src.domain.shared.entity import EntityMeta
from src.domain.shared.statuses import AccessStatus, PaymentStatus

from ..payment_intent.entity import PaymentIntent
from .events import CourseAccessExpired, CourseAccessGranted, CourseAccessRevoked
from .value_objects import AccessSubject, AccessWindow


@dataclass(slots=True)
class CourseAccessGrant:
    """Aggregate Root доступа ученика к курсу."""

    access_grant_id: str
    payment_intent_id: str
    subject: AccessSubject
    status: AccessStatus
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    revoked_by: str | None
    revoke_reason: str | None
    meta: EntityMeta
    events: list[object] = field(default_factory=list)

    @classmethod
    def create_pending(
        cls,
        access_grant_id: str,
        payment_intent_id: str,
        subject: AccessSubject,
        created_at: datetime,
        created_by: str,
    ) -> "CourseAccessGrant":
        """Создает заготовку доступа в pending."""

        if not access_grant_id.strip():
            raise InvariantViolationError("access_grant_id обязателен.")
        if not payment_intent_id.strip():
            raise InvariantViolationError("payment_intent_id обязателен.")

        return cls(
            access_grant_id=access_grant_id,
            payment_intent_id=payment_intent_id,
            subject=subject,
            status=AccessStatus.PENDING,
            granted_at=None,
            expires_at=None,
            revoked_at=None,
            revoked_by=None,
            revoke_reason=None,
            meta=EntityMeta.create(at=created_at, actor_id=created_by),
        )

    @classmethod
    def from_approved_intent(
        cls,
        access_grant_id: str,
        intent: PaymentIntent,
        activated_by: str,
        activated_at: datetime,
        expires_at: datetime | None = None,
    ) -> "CourseAccessGrant":
        """Создает доступ из подтвержденной оплаты."""

        if intent.status != PaymentStatus.APPROVED:
            raise InvariantViolationError(
                "Доступ к курсу можно создать только по approved intent."
            )
        entity = cls.create_pending(
            access_grant_id=access_grant_id,
            payment_intent_id=intent.payment_intent_id,
            subject=AccessSubject(
                course_id=intent.context.course_id,
                student_id=intent.context.student_id,
            ),
            created_at=activated_at,
            created_by=activated_by,
        )
        entity.activate(
            by_admin_id=activated_by,
            at=activated_at,
            expires_at=expires_at,
        )
        return entity

    def activate(
        self,
        by_admin_id: str,
        at: datetime,
        expires_at: datetime | None = None,
    ) -> None:
        """Активирует доступ к курсу."""

        if self.status not in {AccessStatus.PENDING, AccessStatus.EXPIRED}:
            raise InvariantViolationError(
                "Активировать можно только pending или expired доступ."
            )
        window = AccessWindow(granted_at=at, expires_at=expires_at)
        self.status = AccessStatus.ACTIVE
        self.granted_at = window.granted_at
        self.expires_at = window.expires_at
        self.revoked_at = None
        self.revoked_by = None
        self.revoke_reason = None
        self.meta.touch(at=at, actor_id=by_admin_id)
        self.events.append(
            CourseAccessGranted(
                access_grant_id=self.access_grant_id,
                payment_intent_id=self.payment_intent_id,
                course_id=self.subject.course_id,
                student_id=self.subject.student_id,
                occurred_at=at,
            )
        )

    def revoke(self, by_admin_id: str, at: datetime, reason: str | None = None) -> None:
        """Отзывает доступ к курсу."""

        if self.status != AccessStatus.ACTIVE:
            raise InvariantViolationError("Отозвать можно только active доступ.")
        self.status = AccessStatus.REVOKED
        self.revoked_at = at
        self.revoked_by = by_admin_id
        self.revoke_reason = reason.strip() if reason else None
        self.meta.touch(at=at, actor_id=by_admin_id)
        self.events.append(
            CourseAccessRevoked(
                access_grant_id=self.access_grant_id,
                revoked_by=by_admin_id,
                reason=self.revoke_reason,
                occurred_at=at,
            )
        )

    def expire(self, at: datetime, changed_by: str = "system") -> None:
        """Переводит доступ в expired."""

        if self.status != AccessStatus.ACTIVE:
            raise InvariantViolationError(
                "В expired можно перевести только active доступ."
            )
        self.status = AccessStatus.EXPIRED
        self.meta.touch(at=at, actor_id=changed_by)
        self.events.append(
            CourseAccessExpired(
                access_grant_id=self.access_grant_id,
                occurred_at=at,
            )
        )
