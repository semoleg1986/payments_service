"""Репозиторий агрегата CourseAccessGrant."""

from __future__ import annotations

from typing import Protocol

from src.domain.shared.statuses import AccessStatus

from .entity import CourseAccessGrant


class CourseAccessGrantRepository(Protocol):
    """Контракт репозитория доступов к курсам."""

    def get(self, access_grant_id: str) -> CourseAccessGrant | None:
        """Возвращает доступ по id или None."""

    def get_by_payment_intent(self, payment_intent_id: str) -> CourseAccessGrant | None:
        """Возвращает доступ по payment_intent_id или None."""

    def find_by_course_and_student(
        self, course_id: str, student_id: str
    ) -> CourseAccessGrant | None:
        """Ищет доступ для пары course/student."""

    def exists_by_course_and_student_with_status(
        self,
        course_id: str,
        student_id: str,
        status: AccessStatus,
    ) -> bool:
        """Проверяет наличие доступа с указанным статусом."""

    def save(self, access_grant: CourseAccessGrant) -> None:
        """Сохраняет агрегат доступа."""
