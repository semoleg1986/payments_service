"""Unit-тесты application facade."""

from __future__ import annotations

from src.application.contracts.commands import (
    ApprovePaymentIntentCommand,
    CreatePaymentIntentCommand,
)
from src.domain.errors import AccessDeniedError
from src.infrastructure.di.composition import build_runtime


def test_create_and_approve_payment_happy_path() -> None:
    runtime = build_runtime()
    facade = runtime.facade

    payment = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            course_id="course-1",
            attribution_token="promo10-campaign",
            bonus_amount=None,
            idempotency_key="idem-101",
            actor_id="parent-1",
            actor_roles=("parent",),
        )
    )
    assert payment.status == "pending"
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
    assert grant.student_id == "student-1"


def test_admin_can_create_payment_intent_for_parent() -> None:
    runtime = build_runtime()
    facade = runtime.facade

    payment = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            course_id="course-1",
            attribution_token=None,
            bonus_amount=None,
            idempotency_key="idem-admin-201",
            actor_id="admin-1",
            actor_roles=("admin",),
        )
    )

    assert payment.status == "pending"
    assert payment.parent_id == "parent-1"


def test_denied_admin_approve_attempt_is_retained_as_audit_evidence() -> None:
    runtime = build_runtime()
    facade = runtime.facade

    payment = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id="",
            parent_id="parent-1",
            student_id="student-1",
            course_id="course-1",
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
