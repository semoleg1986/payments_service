"""Доменные события агрегата CourseAccessGrant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CourseAccessGranted:
    """Событие активации доступа к курсу."""

    access_grant_id: str
    payment_intent_id: str
    course_id: str
    student_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CourseAccessRevoked:
    """Событие отзыва доступа к курсу."""

    access_grant_id: str
    revoked_by: str
    reason: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CourseAccessExpired:
    """Событие истечения доступа к курсу."""

    access_grant_id: str
    occurred_at: datetime
