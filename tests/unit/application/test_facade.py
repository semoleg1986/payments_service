"""Unit-тесты application facade."""

from __future__ import annotations

from src.application.contracts import OutboxEventStatus, OutboxEventType
from src.application.contracts.commands import (
    ApprovePaymentIntentCommand,
    CreatePaymentIntentCommand,
    RejectPaymentIntentCommand,
)
from src.application.contracts.queries import (
    GetCheckoutStateQuery,
    GetPaymentIntentQuery,
    ListPaymentIntentsQuery,
)
from src.domain.errors import AccessDeniedError
from src.domain.payments.payment_intent.value_objects import PaymentIntentRejectReason
from src.infrastructure.di.composition import build_runtime
from src.infrastructure.integrations.in_memory.bonus_wallet import (
    InMemoryBonusWalletPort,
)
from src.infrastructure.integrations.in_memory.course_access_sync import (
    InMemoryCourseAccessSyncPort,
)


class _FailingCourseAccessSyncPort(InMemoryCourseAccessSyncPort):
    def sync_course_access_granted(self, **kwargs) -> None:  # type: ignore[override]
        raise RuntimeError("sync failed")


class _ObservedBonusWalletPort(InMemoryBonusWalletPort):
    def __init__(self) -> None:
        self.commits: list[tuple[str, int, str, str]] = []

    def commit_redeem(
        self,
        *,
        parent_id: str,
        amount: int,
        payment_intent_id: str,
        idempotency_key: str,
    ) -> None:
        self.commits.append((parent_id, amount, payment_intent_id, idempotency_key))


def test_create_and_approve_payment_happy_path() -> None:
    runtime = build_runtime()
    facade = runtime.facade

    payment = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token="promo10-campaign",
            bonus_amount=None,
            idempotency_key="idem-101",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )
    assert payment.status == "pending"
    assert payment.offer_id == "course-1-standard"
    assert payment.course_id == "course-1"
    assert payment.final_price == 108.0

    grant = facade.approve_payment_intent(
        ApprovePaymentIntentCommand(
            payment_intent_id=payment.payment_intent_id,
            admin_id="admin-1",
            admin_roles=("admin",),
            access_grant_id="",
        )
    )
    assert grant.status == "active"
    assert grant.offer_id == "course-1-standard"
    assert grant.student_id == "student-1"


def test_admin_can_create_payment_intent_for_parent() -> None:
    runtime = build_runtime()
    facade = runtime.facade

    payment = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-201",
            actor_id="admin-1",
            actor_roles=("admin",),
        )
    )

    assert payment.status == "pending"
    assert payment.parent_id == "parent-1"
    assert payment.offer_id == "course-1-standard"


def test_admin_can_list_payment_intents() -> None:
    runtime = build_runtime()
    facade = runtime.facade

    first = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-list-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )
    second = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-2-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-list-2",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    items = facade.list_payment_intents(
        ListPaymentIntentsQuery(
            actor_id="admin-1",
            actor_roles=("admin",),
            status="pending",
            limit=10,
            offset=0,
        )
    )

    assert len(items) >= 2
    assert {item.payment_intent_id for item in items} >= {
        first.payment_intent_id,
        second.payment_intent_id,
    }


def test_parent_cannot_list_payment_intents() -> None:
    runtime = build_runtime()

    try:
        runtime.facade.list_payment_intents(
            ListPaymentIntentsQuery(
                actor_id="parent-1",
                actor_roles=("parent",),
                status="pending",
            )
        )
    except AccessDeniedError:
        pass
    else:
        raise AssertionError("Expected AccessDeniedError")


def test_admin_can_get_payment_intent() -> None:
    runtime = build_runtime()
    payment = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-get-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    result = runtime.facade.get_payment_intent(
        GetPaymentIntentQuery(
            payment_intent_id=payment.payment_intent_id,
            actor_id="admin-1",
            actor_roles=("admin",),
        )
    )

    assert result.payment_intent_id == payment.payment_intent_id


def test_parent_can_get_checkout_state_for_pending_intent() -> None:
    runtime = build_runtime()
    payment = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-checkout-state-pending-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    result = runtime.facade.get_checkout_state(
        GetCheckoutStateQuery(
            actor_id="parent-1",
            actor_roles=("parent",),
            student_id="student-1",
            course_id="course-1",
        )
    )

    assert result.checkout_state == "pending_payment"
    assert result.selected_offer is not None
    assert result.selected_offer.offer_id == "course-1-standard"
    assert result.purchased_offer is None
    assert result.latest_payment_intent is not None
    assert result.latest_payment_intent.payment_intent_id == payment.payment_intent_id
    assert result.access_grant is None
    assert result.available_actions.can_create_payment_intent is False
    assert result.available_actions.next_action == "wait_for_approval"


def test_create_auto_rejects_older_pending_intent() -> None:
    runtime = build_runtime()
    first = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-auto-stale-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    second = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-auto-stale-2",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    first_after = runtime.facade.get_payment_intent(
        GetPaymentIntentQuery(
            payment_intent_id=first.payment_intent_id,
            actor_id="admin-1",
            actor_roles=("admin",),
        )
    )
    second_after = runtime.facade.get_payment_intent(
        GetPaymentIntentQuery(
            payment_intent_id=second.payment_intent_id,
            actor_id="admin-1",
            actor_roles=("admin",),
        )
    )

    assert first_after.status == "rejected"
    assert first_after.rejected_reason == "stale_pending_intent"
    assert second_after.status == "pending"


def test_parent_can_get_checkout_state_for_active_access() -> None:
    runtime = build_runtime()
    payment = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-checkout-state-access-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )
    grant = runtime.facade.approve_payment_intent(
        ApprovePaymentIntentCommand(
            payment_intent_id=payment.payment_intent_id,
            admin_id="admin-1",
            admin_roles=("admin",),
            access_grant_id="",
        )
    )

    result = runtime.facade.get_checkout_state(
        GetCheckoutStateQuery(
            actor_id="parent-1",
            actor_roles=("parent",),
            student_id="student-1",
            course_id="course-1",
        )
    )

    assert result.checkout_state == "access_granted"
    assert result.selected_offer is not None
    assert result.selected_offer.offer_id == "course-1-standard"
    assert result.purchased_offer is not None
    assert result.purchased_offer.access_grant_id == grant.access_grant_id
    assert result.access_grant is not None
    assert result.access_grant.access_grant_id == grant.access_grant_id
    assert result.available_actions.can_create_payment_intent is False
    assert result.available_actions.next_action == "view_access"


def test_create_after_active_access_auto_rejects_new_pending_with_conflict_reason() -> (
    None
):
    runtime = build_runtime()
    first = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-auto-conflict-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )
    runtime.facade.approve_payment_intent(
        ApprovePaymentIntentCommand(
            payment_intent_id=first.payment_intent_id,
            admin_id="admin-1",
            admin_roles=("admin",),
            access_grant_id="",
        )
    )

    second = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-auto-conflict-2",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    second_after = runtime.facade.get_payment_intent(
        GetPaymentIntentQuery(
            payment_intent_id=second.payment_intent_id,
            actor_id="admin-1",
            actor_roles=("admin",),
        )
    )

    assert second_after.status == "rejected"
    assert second_after.rejected_reason == "conflict_existing_access"


def test_admin_payment_view_marks_conflict_existing_access() -> None:
    runtime = build_runtime()
    first = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-conflict-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )
    runtime.facade.approve_payment_intent(
        ApprovePaymentIntentCommand(
            payment_intent_id=first.payment_intent_id,
            admin_id="admin-1",
            admin_roles=("admin",),
            access_grant_id="",
        )
    )
    second = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-conflict-2",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    result = runtime.facade.get_payment_intent(
        GetPaymentIntentQuery(
            payment_intent_id=second.payment_intent_id,
            actor_id="admin-1",
            actor_roles=("admin",),
        )
    )

    assert result.review_state == "rejected"
    assert result.rejected_reason == "conflict_existing_access"
    assert result.recommended_reject_reason == "conflict_existing_access"


def test_admin_reject_persists_enum_reason_in_view() -> None:
    runtime = build_runtime()
    payment = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-reject-view-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    result = runtime.facade.reject_payment_intent(
        RejectPaymentIntentCommand(
            payment_intent_id=payment.payment_intent_id,
            admin_id="admin-1",
            admin_roles=("admin",),
            reason=PaymentIntentRejectReason.STALE_PENDING_INTENT,
        )
    )

    assert result.status == "rejected"
    assert result.rejected_reason == "stale_pending_intent"
    assert result.review_state == "rejected"
    assert result.recommended_reject_reason == "stale_pending_intent"


def test_denied_admin_approve_attempt_is_retained_as_audit_evidence() -> None:
    runtime = build_runtime()
    facade = runtime.facade

    payment = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-denied-approve-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    try:
        facade.approve_payment_intent(
            ApprovePaymentIntentCommand(
                payment_intent_id=payment.payment_intent_id,
                admin_id="parent-1",
                admin_roles=("parent",),
                access_grant_id="",
                request_id="req-denied-approve-1",
                correlation_id="corr-denied-approve-1",
            )
        )
    except AccessDeniedError:
        pass
    else:
        raise AssertionError("Expected AccessDeniedError")

    records = runtime.audit_repo.list_all()
    assert len(records) == 1
    assert records[0].action == "payment_intent.approve"
    assert records[0].result == "denied"
    assert records[0].payment_intent_id == payment.payment_intent_id
    assert records[0].request_id == "req-denied-approve-1"
    assert records[0].correlation_id == "corr-denied-approve-1"
    assert records[0].reason_code == "admin_decision_forbidden"


def test_approve_persists_pending_outbox_when_side_effect_fails() -> None:
    runtime = build_runtime()
    runtime.facade.course_access_sync = _FailingCourseAccessSyncPort()
    observed_bonus = _ObservedBonusWalletPort()
    runtime.facade.bonus_wallet = observed_bonus

    payment = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=12,
            idempotency_key="idem-outbox-failure-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    grant = runtime.facade.approve_payment_intent(
        ApprovePaymentIntentCommand(
            payment_intent_id=payment.payment_intent_id,
            admin_id="admin-1",
            admin_roles=("admin",),
            access_grant_id="",
        )
    )

    assert grant.status == "active"
    pending = runtime.facade.outbox_repo.list_pending_by_aggregate(
        aggregate_id=payment.payment_intent_id
    )
    assert len(pending) == 1
    assert pending[0].event_type == OutboxEventType.COURSE_ACCESS_GRANTED_SYNC
    assert pending[0].status == OutboxEventStatus.PENDING
    assert pending[0].attempt_count == 1
    assert observed_bonus.commits == [
        (
            "parent-1",
            12,
            payment.payment_intent_id,
            f"payment-approve:{payment.payment_intent_id}",
        )
    ]


def test_dispatch_pending_side_effects_retries_and_marks_processed() -> None:
    runtime = build_runtime()
    payment = runtime.facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            offer_id="course-1-standard",
            attribution_token=None,
            bonus_amount=0,
            idempotency_key="idem-outbox-retry-1",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )

    runtime.facade.course_access_sync = _FailingCourseAccessSyncPort()
    runtime.facade.approve_payment_intent(
        ApprovePaymentIntentCommand(
            payment_intent_id=payment.payment_intent_id,
            admin_id="admin-1",
            admin_roles=("admin",),
            access_grant_id="",
        )
    )

    pending_before = runtime.facade.outbox_repo.list_pending_by_aggregate(
        aggregate_id=payment.payment_intent_id
    )
    assert len(pending_before) == 1
    assert pending_before[0].attempt_count == 1

    runtime.facade.course_access_sync = InMemoryCourseAccessSyncPort()
    runtime.facade.dispatch_pending_side_effects(aggregate_id=payment.payment_intent_id)

    pending_after = runtime.facade.outbox_repo.list_pending_by_aggregate(
        aggregate_id=payment.payment_intent_id
    )
    assert pending_after == []
