"""Unit-тесты application facade."""

from __future__ import annotations

from src.application.contracts.commands import (
    ApprovePaymentIntentCommand,
    CreatePaymentIntentCommand,
)
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
