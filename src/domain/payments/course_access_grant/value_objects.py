"""Value Objects агрегата CourseAccessGrant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.errors import InvariantViolationError


@dataclass(frozen=True, slots=True)
class AccessSubject:
    """Связка курса и ученика для выдачи доступа."""

    course_id: str
    student_id: str

    def __post_init__(self) -> None:
        if not self.course_id.strip():
            raise InvariantViolationError("course_id обязателен.")
        if not self.student_id.strip():
            raise InvariantViolationError("student_id обязателен.")


@dataclass(frozen=True, slots=True)
class AccessWindow:
    """Окно действия доступа к курсу."""

    granted_at: datetime
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.expires_at is not None and self.expires_at <= self.granted_at:
            raise InvariantViolationError("expires_at должен быть позже granted_at.")
