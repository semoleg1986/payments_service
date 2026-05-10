"""Реализация фасада application-слоя payments_service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

from src.application.contracts.commands import (
    ApprovePaymentIntentCommand,
    CancelPaymentIntentCommand,
    CreatePaymentIntentCommand,
    RejectPaymentIntentCommand,
)
from src.application.contracts.facade import (
    AccessCheckView,
    CourseAccessGrantView,
    PaymentIntentView,
)
from src.application.contracts.ports import (
    AttributionDiscountPort,
    AuditEvidenceRecord,
    AuditEvidenceRepositoryPort,
    BonusQuoteSnapshot,
    BonusWalletPort,
    Clock,
    CourseAccessGrantRepositoryPort,
    CourseAccessSyncPort,
    CourseCatalogPort,
    IdGenerator,
    OutboxEventRecord,
    OutboxEventRepositoryPort,
    OutboxEventStatus,
    OutboxEventType,
    PaymentIntentRepositoryPort,
    UnitOfWorkFactory,
    UserRelationsPort,
)
from src.application.contracts.queries import (
    GetCourseAccessGrantQuery,
    GetPaymentIntentQuery,
    ListPaymentsByParentQuery,
)
from src.domain.errors import AccessDeniedError, NotFoundError
from src.domain.payments.course_access_grant.entity import CourseAccessGrant
from src.domain.payments.course_access_grant.policies import (
    ensure_no_other_active_access,
)
from src.domain.payments.payment_intent.entity import PaymentIntent
from src.domain.payments.payment_intent.policies import (
    ensure_admin_can_decide,
    ensure_parent_can_create_intent,
)
from src.domain.payments.payment_intent.value_objects import (
    Discount,
    Money,
    PaymentContext,
)
from src.domain.shared.statuses import AccessStatus, PaymentStatus


@dataclass(slots=True)
class PaymentApplicationFacade:
    """Фасад use-cases платежного сервиса."""

    payment_repo: PaymentIntentRepositoryPort
    access_repo: CourseAccessGrantRepositoryPort
    course_catalog: CourseCatalogPort
    user_relations: UserRelationsPort
    attribution: AttributionDiscountPort
    bonus_wallet: BonusWalletPort
    id_generator: IdGenerator
    clock: Clock
    uow_factory: UnitOfWorkFactory
    audit_repo: AuditEvidenceRepositoryPort
    outbox_repo: OutboxEventRepositoryPort
    course_access_sync: CourseAccessSyncPort | None = None

    def create_payment_intent(
        self, command: CreatePaymentIntentCommand
    ) -> PaymentIntentView:
        """Создает intent на оплату курса."""

        ensure_parent_can_create_intent(command.actor_id, list(command.actor_roles))

        if (
            "parent" in set(command.actor_roles)
            and command.actor_id != command.parent_id
        ):
            raise AccessDeniedError(
                "parent может создавать оплату только от своего имени."
            )

        if not self.user_relations.is_parent_of_student(
            parent_id=command.parent_id,
            student_id=command.student_id,
        ):
            raise AccessDeniedError("parent_id не связан с student_id.")

        if command.idempotency_key:
            existing = self.payment_repo.get_by_idempotency_key(
                parent_id=command.parent_id,
                idempotency_key=command.idempotency_key,
            )
            if existing is not None:
                return self._to_payment_view(existing)

        course = self.course_catalog.get_course(command.course_id)
        if course is None:
            raise NotFoundError("Курс не найден.")

        effective_payment_intent_id = (
            command.payment_intent_id or self.id_generator.new_id()
        )

        discount_snapshot = self.attribution.resolve_discount(
            attribution_token=command.attribution_token,
            course_id=command.course_id,
            parent_id=command.parent_id,
        )
        bonus_snapshot = self._resolve_bonus_quote(
            command=command,
            payment_intent_id=effective_payment_intent_id,
        )

        now = self.clock.now()
        intent = PaymentIntent.create(
            payment_intent_id=effective_payment_intent_id,
            context=PaymentContext(
                parent_id=command.parent_id,
                student_id=command.student_id,
                course_id=command.course_id,
                attribution_token=command.attribution_token,
                bonus_amount=bonus_snapshot.allowed_amount,
                idempotency_key=command.idempotency_key,
            ),
            base_price=Money(amount=course.price, currency=course.currency),
            discount=Discount(
                kind=discount_snapshot.kind, value=discount_snapshot.value
            ),
            created_at=now,
            created_by=command.actor_id,
        )

        with self.uow_factory() as uow:
            self.payment_repo.save(intent)
            uow.commit()
        return self._to_payment_view(intent)

    def approve_payment_intent(
        self, command: ApprovePaymentIntentCommand
    ) -> CourseAccessGrantView:
        """Подтверждает intent и активирует доступ к курсу."""

        try:
            ensure_admin_can_decide(command.admin_id, list(command.admin_roles))
        except AccessDeniedError as exc:
            self._append_denied_admin_decision(
                action="payment_intent.approve",
                payment_intent_id=command.payment_intent_id,
                actor_id=command.admin_id,
                actor_roles=command.admin_roles,
                reason=str(exc),
                reason_code="admin_decision_forbidden",
                request_id=command.request_id,
                correlation_id=command.correlation_id,
            )
            raise
        intent = self.payment_repo.get(command.payment_intent_id)
        if intent is None:
            raise NotFoundError("PaymentIntent не найден.")

        now = self.clock.now()
        existing_grant = self.access_repo.get_by_payment_intent(
            intent.payment_intent_id
        )

        if intent.status == PaymentStatus.PENDING:
            intent.approve(admin_id=command.admin_id, approved_at=now)
        elif intent.status != PaymentStatus.APPROVED:
            raise AccessDeniedError(
                "Подтверждение возможно только для pending/approved."
            )

        if existing_grant is not None:
            self.dispatch_pending_side_effects(
                aggregate_id=existing_grant.payment_intent_id
            )
            return self._to_access_view(existing_grant)

        ensure_no_other_active_access(
            has_active_access=self.access_repo.exists_active_by_course_and_student(
                course_id=intent.context.course_id,
                student_id=intent.context.student_id,
            ),
            course_id=intent.context.course_id,
            student_id=intent.context.student_id,
        )

        course = self.course_catalog.get_course(intent.context.course_id)
        if course is None:
            raise NotFoundError("Курс не найден.")

        expires_at = None
        if course.access_ttl_days is not None:
            expires_at = now + timedelta(days=course.access_ttl_days)

        grant = CourseAccessGrant.from_approved_intent(
            access_grant_id=command.access_grant_id or self.id_generator.new_id(),
            intent=intent,
            activated_by=command.admin_id,
            activated_at=now,
            expires_at=expires_at,
        )

        with self.uow_factory() as uow:
            self.payment_repo.save(intent)
            self.access_repo.save(grant)
            self._enqueue_approval_side_effects(intent=intent, grant=grant)
            uow.commit()
        self.dispatch_pending_side_effects(aggregate_id=intent.payment_intent_id)
        return self._to_access_view(grant)

    def reject_payment_intent(
        self, command: RejectPaymentIntentCommand
    ) -> PaymentIntentView:
        """Отклоняет intent администратором."""

        try:
            ensure_admin_can_decide(command.admin_id, list(command.admin_roles))
        except AccessDeniedError as exc:
            self._append_denied_admin_decision(
                action="payment_intent.reject",
                payment_intent_id=command.payment_intent_id,
                actor_id=command.admin_id,
                actor_roles=command.admin_roles,
                reason=str(exc),
                reason_code="admin_decision_forbidden",
                request_id=command.request_id,
                correlation_id=command.correlation_id,
            )
            raise
        intent = self.payment_repo.get(command.payment_intent_id)
        if intent is None:
            raise NotFoundError("PaymentIntent не найден.")

        intent.reject(
            admin_id=command.admin_id,
            rejected_at=self.clock.now(),
            reason=command.reason,
        )
        with self.uow_factory() as uow:
            self.payment_repo.save(intent)
            uow.commit()
        return self._to_payment_view(intent)

    def cancel_payment_intent(
        self, command: CancelPaymentIntentCommand
    ) -> PaymentIntentView:
        """Отменяет intent владельцем-parent."""

        ensure_parent_can_create_intent(command.actor_id, list(command.actor_roles))
        intent = self.payment_repo.get(command.payment_intent_id)
        if intent is None:
            raise NotFoundError("PaymentIntent не найден.")

        intent.cancel(actor_id=command.actor_id, cancelled_at=self.clock.now())
        with self.uow_factory() as uow:
            self.payment_repo.save(intent)
            uow.commit()
        return self._to_payment_view(intent)

    def get_payment_intent(self, query: GetPaymentIntentQuery) -> PaymentIntentView:
        """Возвращает intent по id c базовой проверкой доступа."""

        intent = self.payment_repo.get(query.payment_intent_id)
        if intent is None:
            raise NotFoundError("PaymentIntent не найден.")

        roles = set(query.actor_roles)
        if "admin" not in roles and intent.context.parent_id != query.actor_id:
            raise AccessDeniedError("Нет доступа к PaymentIntent.")
        return self._to_payment_view(intent)

    def get_course_access_grant(
        self,
        query: GetCourseAccessGrantQuery,
    ) -> CourseAccessGrantView:
        """Возвращает доступ по id c базовой проверкой ролей."""

        grant = self.access_repo.get(query.access_grant_id)
        if grant is None:
            raise NotFoundError("CourseAccessGrant не найден.")
        roles = set(query.actor_roles)
        if "admin" not in roles and "parent" not in roles:
            raise AccessDeniedError("Нет доступа к CourseAccessGrant.")
        return self._to_access_view(grant)

    def list_payments_by_parent(
        self,
        query: ListPaymentsByParentQuery,
    ) -> list[PaymentIntentView]:
        """Возвращает список платежей родителя."""

        roles = set(query.actor_roles)
        if "admin" not in roles and query.parent_id != query.actor_id:
            raise AccessDeniedError("Нет доступа к списку платежей.")
        return [
            self._to_payment_view(x)
            for x in self.payment_repo.list_by_parent(query.parent_id)
        ]

    def check_course_access(self, course_id: str, student_id: str) -> AccessCheckView:
        """Проверяет наличие active доступа к курсу."""

        grant = self.access_repo.find_by_course_and_student(
            course_id=course_id,
            student_id=student_id,
        )
        if grant is None or grant.status != AccessStatus.ACTIVE:
            return AccessCheckView(
                has_access=False,
                course_id=course_id,
                student_id=student_id,
            )
        return AccessCheckView(
            has_access=True,
            course_id=course_id,
            student_id=student_id,
            access_grant_id=grant.access_grant_id,
            status=grant.status.value,
            expires_at=grant.expires_at,
        )

    @staticmethod
    def _to_payment_view(intent: PaymentIntent) -> PaymentIntentView:
        return PaymentIntentView(
            payment_intent_id=intent.payment_intent_id,
            parent_id=intent.context.parent_id,
            student_id=intent.context.student_id,
            course_id=intent.context.course_id,
            status=intent.status.value,
            base_price=float(intent.base_price.amount),
            final_price=float(intent.final_price.amount),
            bonus_amount=int(intent.context.bonus_amount),
            currency=intent.final_price.currency,
            expires_at=intent.context.expires_at,
            created_at=intent.meta.created_at,
            updated_at=intent.meta.updated_at,
            version=intent.meta.version,
        )

    @staticmethod
    def _to_access_view(grant: CourseAccessGrant) -> CourseAccessGrantView:
        return CourseAccessGrantView(
            access_grant_id=grant.access_grant_id,
            payment_intent_id=grant.payment_intent_id,
            course_id=grant.subject.course_id,
            student_id=grant.subject.student_id,
            status=grant.status.value,
            granted_at=grant.granted_at,
            expires_at=grant.expires_at,
            revoked_at=grant.revoked_at,
            created_at=grant.meta.created_at,
            updated_at=grant.meta.updated_at,
            version=grant.meta.version,
        )

    def _append_denied_admin_decision(
        self,
        *,
        action: str,
        payment_intent_id: str,
        actor_id: str,
        actor_roles: tuple[str, ...],
        reason: str,
        reason_code: str,
        request_id: str | None,
        correlation_id: str | None,
    ) -> None:
        record = AuditEvidenceRecord(
            audit_id=self.id_generator.new_id(),
            action=action,
            occurred_at=self.clock.now(),
            result="denied",
            actor_id=actor_id or None,
            actor_roles=tuple(actor_roles),
            target_type="payment_intent",
            target_id=payment_intent_id or None,
            reason=reason,
            reason_code=reason_code,
            request_id=request_id,
            correlation_id=correlation_id,
            payment_intent_id=payment_intent_id or None,
        )
        with self.uow_factory() as uow:
            self.audit_repo.append(record)
            uow.commit()

    def _sync_course_access_granted(self, grant: CourseAccessGrant) -> None:
        if self.course_access_sync is None:
            return
        self.course_access_sync.sync_course_access_granted(
            event_id=f"{grant.access_grant_id}:granted",
            course_id=grant.subject.course_id,
            student_id=grant.subject.student_id,
            granted_status="approved",
        )

    def _resolve_bonus_quote(
        self,
        *,
        command: CreatePaymentIntentCommand,
        payment_intent_id: str,
    ) -> BonusQuoteSnapshot:
        requested_amount = command.bonus_amount or 0
        if requested_amount <= 0:
            return BonusQuoteSnapshot(requested_amount=0, allowed_amount=0)
        return self.bonus_wallet.quote_redeem(
            parent_id=command.parent_id,
            requested_amount=requested_amount,
            payment_intent_id=payment_intent_id,
        )

    def _commit_bonus_redeem(self, intent: PaymentIntent) -> None:
        if intent.context.bonus_amount <= 0:
            return
        self.bonus_wallet.commit_redeem(
            parent_id=intent.context.parent_id,
            amount=intent.context.bonus_amount,
            payment_intent_id=intent.payment_intent_id,
            idempotency_key=f"payment-approve:{intent.payment_intent_id}",
        )

    def dispatch_pending_side_effects(
        self,
        *,
        aggregate_id: str | None = None,
        limit: int = 100,
    ) -> None:
        """Доставляет pending outbox-события после локального commit."""

        if aggregate_id is None:
            events = self.outbox_repo.list_pending(limit=limit)
        else:
            events = self.outbox_repo.list_pending_by_aggregate(
                aggregate_id=aggregate_id
            )

        for event in events:
            try:
                self._dispatch_outbox_event(event)
            except Exception as exc:
                self.outbox_repo.save(event.mark_failed(error=str(exc)))
            else:
                self.outbox_repo.save(event.mark_processed(at=self.clock.now()))

    def _enqueue_approval_side_effects(
        self,
        *,
        intent: PaymentIntent,
        grant: CourseAccessGrant,
    ) -> None:
        created_at = self.clock.now()
        self.outbox_repo.add(
            OutboxEventRecord(
                event_id=self.id_generator.new_id(),
                aggregate_type="payment_intent",
                aggregate_id=intent.payment_intent_id,
                event_type=OutboxEventType.COURSE_ACCESS_GRANTED_SYNC,
                payload_json=json.dumps(
                    {
                        "access_grant_id": grant.access_grant_id,
                        "payment_intent_id": intent.payment_intent_id,
                        "course_id": grant.subject.course_id,
                        "student_id": grant.subject.student_id,
                        "granted_status": "approved",
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                ),
                status=OutboxEventStatus.PENDING,
                attempt_count=0,
                available_at=created_at,
                created_at=created_at,
            )
        )

        if intent.context.bonus_amount > 0:
            self.outbox_repo.add(
                OutboxEventRecord(
                    event_id=self.id_generator.new_id(),
                    aggregate_type="payment_intent",
                    aggregate_id=intent.payment_intent_id,
                    event_type=OutboxEventType.BONUS_REDEEM_COMMIT,
                    payload_json=json.dumps(
                        {
                            "parent_id": intent.context.parent_id,
                            "amount": int(intent.context.bonus_amount),
                            "payment_intent_id": intent.payment_intent_id,
                            "idempotency_key": (
                                f"payment-approve:{intent.payment_intent_id}"
                            ),
                        },
                        ensure_ascii=True,
                        sort_keys=True,
                    ),
                    status=OutboxEventStatus.PENDING,
                    attempt_count=0,
                    available_at=created_at,
                    created_at=created_at,
                )
            )

    def _dispatch_outbox_event(self, event: OutboxEventRecord) -> None:
        payload = json.loads(event.payload_json)
        if event.event_type == OutboxEventType.COURSE_ACCESS_GRANTED_SYNC:
            if self.course_access_sync is None:
                raise RuntimeError("CourseAccessSyncPort не настроен.")
            self.course_access_sync.sync_course_access_granted(
                event_id=payload["access_grant_id"],
                course_id=payload["course_id"],
                student_id=payload["student_id"],
                granted_status=payload["granted_status"],
            )
            return

        if event.event_type == OutboxEventType.BONUS_REDEEM_COMMIT:
            self.bonus_wallet.commit_redeem(
                parent_id=payload["parent_id"],
                amount=int(payload["amount"]),
                payment_intent_id=payload["payment_intent_id"],
                idempotency_key=payload["idempotency_key"],
            )
            return

        raise RuntimeError(f"Неизвестный тип outbox-события: {event.event_type}")
