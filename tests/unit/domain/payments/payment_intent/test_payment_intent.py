"""Unit-тесты агрегата PaymentIntent."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.domain.errors import InvariantViolationError
from src.domain.payments.payment_intent.entity import PaymentIntent
from src.domain.payments.payment_intent.value_objects import (
    Discount,
    Money,
    PaymentContext,
)
from src.domain.shared.statuses import PaymentStatus


def _now() -> datetime:
    return datetime(2026, 4, 12, 12, 0, 0, tzinfo=UTC)


def _make_intent() -> PaymentIntent:
    now = _now()
    return PaymentIntent.create(
        payment_intent_id="pi-1",
        context=PaymentContext(
            parent_id="parent-1",
            student_id="student-1",
            course_id="course-1",
            idempotency_key="idem-1",
        ),
        base_price=Money(amount=100.0, currency="USD"),
        discount=Discount(kind="percent", value=20.0),
        created_at=now,
        created_by="parent-1",
    )


def test_create_payment_intent_sets_pending_and_final_price() -> None:
    intent = _make_intent()

    assert intent.status == PaymentStatus.PENDING
    assert intent.final_price.amount == 80.0
    assert intent.meta.version == 1
    assert len(intent.events) == 1


def test_approve_payment_intent() -> None:
    intent = _make_intent()

    intent.approve(admin_id="admin-1", approved_at=_now())

    assert intent.status == PaymentStatus.APPROVED
    assert intent.approved_by == "admin-1"
    assert intent.meta.version == 2
    assert len(intent.events) == 2


def test_reject_only_pending() -> None:
    intent = _make_intent()
    intent.approve(admin_id="admin-1", approved_at=_now())

    with pytest.raises(InvariantViolationError):
        intent.reject(admin_id="admin-2", rejected_at=_now(), reason="bad docs")


def test_cancel_only_by_parent() -> None:
    intent = _make_intent()

    with pytest.raises(InvariantViolationError):
        intent.cancel(actor_id="another-parent", cancelled_at=_now())

    intent.cancel(actor_id="parent-1", cancelled_at=_now())
    assert intent.status == PaymentStatus.CANCELLED
