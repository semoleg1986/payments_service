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
    CheckoutActionsView,
    CheckoutOfferView,
    CheckoutStateView,
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
    CommercialCatalogPort,
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
    GetCheckoutStateQuery,
    GetCourseAccessGrantQuery,
    GetPaymentIntentQuery,
    ListPaymentIntentsQuery,
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
    PaymentIntentRejectReason,
)
from src.domain.shared.statuses import AccessStatus, PaymentStatus

AUTO_RECONCILE_ACTOR_ID = "system:auto_reconcile"


@dataclass(slots=True)
class PaymentApplicationFacade:
    """Фасад use-cases платежного сервиса."""

    payment_repo: PaymentIntentRepositoryPort
    access_repo: CourseAccessGrantRepositoryPort
    commercial_catalog: CommercialCatalogPort
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

        offer = self.commercial_catalog.get_offer(command.offer_id)
        if offer is None:
            raise NotFoundError("Offer не найден.")

        course = self.course_catalog.get_course(offer.course_id)
        if course is None:
            raise NotFoundError("Курс для offer не найден.")

        effective_payment_intent_id = (
            command.payment_intent_id or self.id_generator.new_id()
        )

        discount_snapshot = self.attribution.resolve_discount(
            attribution_token=command.attribution_token,
            course_id=offer.course_id,
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
                offer_id=offer.offer_id,
                course_id=offer.course_id,
                attribution_token=command.attribution_token,
                bonus_amount=bonus_snapshot.allowed_amount,
                idempotency_key=command.idempotency_key,
            ),
            base_price=Money(amount=offer.price, currency=offer.currency),
            discount=Discount(
                kind=discount_snapshot.kind, value=discount_snapshot.value
            ),
            created_at=now,
            created_by=command.actor_id,
        )

        with self.uow_factory() as uow:
            self.payment_repo.save(intent)
            self._reconcile_pending_intents_for_student_course(
                parent_id=command.parent_id,
                student_id=command.student_id,
                course_id=offer.course_id,
            )
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
            self._reconcile_pending_intents_for_student_course(
                parent_id=intent.context.parent_id,
                student_id=intent.context.student_id,
                course_id=intent.context.course_id,
            )
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

    def list_payment_intents(
        self,
        query: ListPaymentIntentsQuery,
    ) -> list[PaymentIntentView]:
        """Возвращает список intent-ов для admin queue."""

        if "admin" not in set(query.actor_roles):
            raise AccessDeniedError("Нет доступа к списку PaymentIntent.")

        if query.status == PaymentStatus.PENDING.value:
            raw_items = self.payment_repo.list(
                status=query.status,
                limit=query.limit,
                offset=query.offset,
            )
            pairs = {
                (
                    item.context.parent_id,
                    item.context.student_id,
                    item.context.course_id,
                )
                for item in raw_items
            }
            with self.uow_factory() as uow:
                for parent_id, student_id, course_id in pairs:
                    self._reconcile_pending_intents_for_student_course(
                        parent_id=parent_id,
                        student_id=student_id,
                        course_id=course_id,
                    )
                uow.commit()

        return [
            self._to_payment_view(x)
            for x in self.payment_repo.list(
                status=query.status,
                limit=query.limit,
                offset=query.offset,
            )
        ]

    def get_checkout_state(self, query: GetCheckoutStateQuery) -> CheckoutStateView:
        """Возвращает checkout-state для parent/student/course."""

        ensure_parent_can_create_intent(query.actor_id, list(query.actor_roles))

        if not self.user_relations.is_parent_of_student(
            parent_id=query.actor_id,
            student_id=query.student_id,
        ):
            raise AccessDeniedError("parent_id не связан с student_id.")

        course = self.course_catalog.get_course(query.course_id)
        if course is None:
            raise NotFoundError("Курс не найден.")

        with self.uow_factory() as uow:
            self._reconcile_pending_intents_for_student_course(
                parent_id=query.actor_id,
                student_id=query.student_id,
                course_id=query.course_id,
            )
            uow.commit()

        latest_intent = self.payment_repo.get_latest_by_parent_student_course(
            parent_id=query.actor_id,
            student_id=query.student_id,
            course_id=query.course_id,
        )
        active_grant = self.access_repo.get_active_by_student_and_course(
            course_id=query.course_id,
            student_id=query.student_id,
        )

        latest_intent_view = (
            self._to_payment_view(latest_intent) if latest_intent is not None else None
        )
        active_grant_view = (
            self._to_access_view(active_grant) if active_grant is not None else None
        )
        selected_offer_view = (
            self._to_checkout_offer_view_from_intent(latest_intent_view)
            if latest_intent_view is not None
            else None
        )
        purchased_offer_view = (
            self._to_checkout_offer_view_from_grant(
                active_grant_view, latest_intent_view
            )
            if active_grant_view is not None
            else None
        )

        has_conflicting_pending_intent = (
            active_grant_view is not None
            and latest_intent_view is not None
            and latest_intent_view.payment_intent_id
            != active_grant_view.payment_intent_id
            and latest_intent_view.status == PaymentStatus.PENDING.value
        )

        if has_conflicting_pending_intent:
            checkout_state = "conflict_existing_access"
            actions = CheckoutActionsView(
                can_create_payment_intent=False,
                can_retry_payment=False,
                next_action="view_access",
            )
        elif active_grant_view is not None:
            checkout_state = "access_granted"
            actions = CheckoutActionsView(
                can_create_payment_intent=False,
                can_retry_payment=False,
                next_action="view_access",
            )
        elif latest_intent_view is None:
            checkout_state = "idle"
            actions = CheckoutActionsView(
                can_create_payment_intent=True,
                can_retry_payment=False,
                next_action="create_payment_intent",
            )
        elif latest_intent_view.status == PaymentStatus.PENDING.value:
            checkout_state = "pending_payment"
            actions = CheckoutActionsView(
                can_create_payment_intent=False,
                can_retry_payment=False,
                next_action="wait_for_approval",
                resume_payment_intent_id=latest_intent_view.payment_intent_id,
            )
        elif latest_intent_view.status == PaymentStatus.APPROVED.value:
            checkout_state = "payment_approved"
            actions = CheckoutActionsView(
                can_create_payment_intent=False,
                can_retry_payment=False,
                next_action="wait_for_access_grant",
                resume_payment_intent_id=latest_intent_view.payment_intent_id,
            )
        elif latest_intent_view.status == PaymentStatus.REJECTED.value:
            checkout_state = "payment_rejected"
            actions = CheckoutActionsView(
                can_create_payment_intent=True,
                can_retry_payment=True,
                next_action="retry_payment",
                resume_payment_intent_id=latest_intent_view.payment_intent_id,
            )
        elif latest_intent_view.status == PaymentStatus.CANCELLED.value:
            checkout_state = "payment_cancelled"
            actions = CheckoutActionsView(
                can_create_payment_intent=True,
                can_retry_payment=True,
                next_action="retry_payment",
                resume_payment_intent_id=latest_intent_view.payment_intent_id,
            )
        else:
            checkout_state = "idle"
            actions = CheckoutActionsView(
                can_create_payment_intent=True,
                can_retry_payment=False,
                next_action="create_payment_intent",
            )

        return CheckoutStateView(
            parent_id=query.actor_id,
            student_id=query.student_id,
            course_id=query.course_id,
            checkout_state=checkout_state,
            selected_offer=selected_offer_view,
            purchased_offer=purchased_offer_view,
            latest_payment_intent=latest_intent_view,
            access_grant=active_grant_view,
            available_actions=actions,
        )

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

    def _build_review_state(
        self, intent: PaymentIntent
    ) -> tuple[str, PaymentIntentRejectReason | None]:
        if intent.status == PaymentStatus.PENDING:
            active_grant = self.access_repo.get_active_by_student_and_course(
                course_id=intent.context.course_id,
                student_id=intent.context.student_id,
            )
            if (
                active_grant is not None
                and active_grant.payment_intent_id != intent.payment_intent_id
            ):
                return (
                    "conflict_existing_access",
                    PaymentIntentRejectReason.CONFLICT_EXISTING_ACCESS,
                )

            latest_intent = self.payment_repo.get_latest_by_parent_student_course(
                parent_id=intent.context.parent_id,
                student_id=intent.context.student_id,
                course_id=intent.context.course_id,
            )
            if (
                latest_intent is not None
                and latest_intent.payment_intent_id != intent.payment_intent_id
            ):
                return (
                    "stale_pending_intent",
                    PaymentIntentRejectReason.STALE_PENDING_INTENT,
                )

            return ("ready_for_approval", None)

        if intent.status == PaymentStatus.APPROVED:
            return ("approved", None)
        if intent.status == PaymentStatus.REJECTED:
            return ("rejected", intent.rejected_reason)
        if intent.status == PaymentStatus.CANCELLED:
            return ("cancelled", None)
        if intent.status == PaymentStatus.EXPIRED:
            return ("expired", None)
        return ("ready_for_approval", None)

    def _reconcile_pending_intents_for_student_course(
        self,
        *,
        parent_id: str,
        student_id: str,
        course_id: str,
    ) -> None:
        pending_items = self.payment_repo.list_pending_by_student_and_course(
            student_id=student_id,
            course_id=course_id,
        )
        if not pending_items:
            return

        active_grant = self.access_repo.get_active_by_student_and_course(
            course_id=course_id,
            student_id=student_id,
        )
        if active_grant is not None:
            for intent in pending_items:
                if intent.payment_intent_id == active_grant.payment_intent_id:
                    continue
                intent.reject(
                    admin_id=AUTO_RECONCILE_ACTOR_ID,
                    rejected_at=self.clock.now(),
                    reason=PaymentIntentRejectReason.CONFLICT_EXISTING_ACCESS,
                )
                self.payment_repo.save(intent)
            return

        latest_intent = self.payment_repo.get_latest_by_parent_student_course(
            parent_id=parent_id,
            student_id=student_id,
            course_id=course_id,
        )
        if latest_intent is None or latest_intent.status != PaymentStatus.PENDING:
            return

        for intent in pending_items:
            if intent.context.parent_id != parent_id:
                continue
            if intent.payment_intent_id == latest_intent.payment_intent_id:
                continue
            intent.reject(
                admin_id=AUTO_RECONCILE_ACTOR_ID,
                rejected_at=self.clock.now(),
                reason=PaymentIntentRejectReason.STALE_PENDING_INTENT,
            )
            self.payment_repo.save(intent)

    def _to_payment_view(self, intent: PaymentIntent) -> PaymentIntentView:
        review_state, recommended_reject_reason = self._build_review_state(intent)
        return PaymentIntentView(
            payment_intent_id=intent.payment_intent_id,
            parent_id=intent.context.parent_id,
            student_id=intent.context.student_id,
            offer_id=intent.context.offer_id,
            course_id=intent.context.course_id,
            status=intent.status.value,
            base_price=float(intent.base_price.amount),
            final_price=float(intent.final_price.amount),
            bonus_amount=int(intent.context.bonus_amount),
            currency=intent.final_price.currency,
            expires_at=intent.context.expires_at,
            rejected_reason=(
                intent.rejected_reason.value
                if intent.rejected_reason is not None
                else None
            ),
            review_state=review_state,
            recommended_reject_reason=(
                recommended_reject_reason.value
                if recommended_reject_reason is not None
                else None
            ),
            created_at=intent.meta.created_at,
            updated_at=intent.meta.updated_at,
            version=intent.meta.version,
        )

    @staticmethod
    def _to_access_view(grant: CourseAccessGrant) -> CourseAccessGrantView:
        return CourseAccessGrantView(
            access_grant_id=grant.access_grant_id,
            payment_intent_id=grant.payment_intent_id,
            offer_id=grant.offer_id,
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

    @staticmethod
    def _to_checkout_offer_view_from_intent(
        intent: PaymentIntentView,
    ) -> CheckoutOfferView:
        return CheckoutOfferView(
            offer_id=intent.offer_id,
            course_id=intent.course_id,
            base_price=intent.base_price,
            final_price=intent.final_price,
            bonus_amount=intent.bonus_amount,
            currency=intent.currency,
            source="latest_payment_intent",
            payment_intent_id=intent.payment_intent_id,
        )

    def _to_checkout_offer_view_from_grant(
        self,
        grant: CourseAccessGrantView,
        latest_intent: PaymentIntentView | None,
    ) -> CheckoutOfferView:
        source_intent = latest_intent
        if (
            source_intent is None
            or source_intent.payment_intent_id != grant.payment_intent_id
        ):
            intent = self.payment_repo.get(grant.payment_intent_id)
            source_intent = (
                self._to_payment_view(intent) if intent is not None else None
            )

        if source_intent is not None:
            return CheckoutOfferView(
                offer_id=grant.offer_id,
                course_id=grant.course_id,
                base_price=source_intent.base_price,
                final_price=source_intent.final_price,
                bonus_amount=source_intent.bonus_amount,
                currency=source_intent.currency,
                source="access_grant",
                payment_intent_id=grant.payment_intent_id,
                access_grant_id=grant.access_grant_id,
            )

        offer = self.commercial_catalog.get_offer(grant.offer_id)
        course = self.course_catalog.get_course(grant.course_id)
        currency = (
            offer.currency
            if offer is not None
            else (course.currency if course is not None else "USD")
        )
        base_price = (
            float(offer.price)
            if offer is not None
            else (float(course.price) if course is not None else 0.0)
        )

        return CheckoutOfferView(
            offer_id=grant.offer_id,
            course_id=grant.course_id,
            base_price=base_price,
            final_price=base_price,
            bonus_amount=0,
            currency=currency,
            source="access_grant",
            payment_intent_id=grant.payment_intent_id,
            access_grant_id=grant.access_grant_id,
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
