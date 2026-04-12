"""Unit-тесты агрегата CourseAccessGrant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.errors import InvariantViolationError
from src.domain.payments.course_access_grant.entity import CourseAccessGrant
from src.domain.payments.payment_intent.entity import PaymentIntent
from src.domain.payments.payment_intent.value_objects import (
    Discount,
    Money,
    PaymentContext,
)
from src.domain.shared.statuses import AccessStatus


def _now() -> datetime:
    return datetime(2026, 4, 12, 13, 0, 0, tzinfo=UTC)


def _approved_intent() -> PaymentIntent:
    now = _now()
    intent = PaymentIntent.create(
        payment_intent_id="pi-100",
        context=PaymentContext(
            parent_id="parent-1",
            student_id="student-1",
            course_id="course-1",
            idempotency_key="idem-100",
        ),
        base_price=Money(amount=120.0, currency="USD"),
        discount=Discount(kind="fixed", value=20.0),
        created_at=now,
        created_by="parent-1",
    )
    intent.approve(admin_id="admin-1", approved_at=now)
    return intent


def test_create_from_approved_intent_activates_access() -> None:
    now = _now()
    grant = CourseAccessGrant.from_approved_intent(
        access_grant_id="ag-1",
        intent=_approved_intent(),
        activated_by="admin-1",
        activated_at=now,
        expires_at=now + timedelta(days=30),
    )

    assert grant.status == AccessStatus.ACTIVE
    assert grant.subject.course_id == "course-1"
    assert grant.subject.student_id == "student-1"
    assert grant.meta.version == 2
    assert len(grant.events) == 1


def test_revoke_only_active_access() -> None:
    now = _now()
    grant = CourseAccessGrant.from_approved_intent(
        access_grant_id="ag-2",
        intent=_approved_intent(),
        activated_by="admin-1",
        activated_at=now,
    )

    grant.revoke(by_admin_id="admin-1", at=now, reason="manual lock")
    assert grant.status == AccessStatus.REVOKED
    assert grant.revoke_reason == "manual lock"

    with pytest.raises(InvariantViolationError):
        grant.revoke(by_admin_id="admin-1", at=now)


def test_expire_only_active_access() -> None:
    now = _now()
    grant = CourseAccessGrant.from_approved_intent(
        access_grant_id="ag-3",
        intent=_approved_intent(),
        activated_by="admin-1",
        activated_at=now,
    )

    grant.expire(at=now)
    assert grant.status == AccessStatus.EXPIRED

    with pytest.raises(InvariantViolationError):
        grant.expire(at=now)
