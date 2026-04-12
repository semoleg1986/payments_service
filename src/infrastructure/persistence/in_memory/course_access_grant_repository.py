"""In-memory репозиторий CourseAccessGrant."""

from __future__ import annotations

from src.domain.payments.course_access_grant.entity import CourseAccessGrant
from src.domain.shared.statuses import AccessStatus


class InMemoryCourseAccessGrantRepository:
    """Хранилище CourseAccessGrant в памяти процесса."""

    def __init__(self) -> None:
        self._items: dict[str, CourseAccessGrant] = {}

    def get(self, access_grant_id: str) -> CourseAccessGrant | None:
        return self._items.get(access_grant_id)

    def get_by_payment_intent(self, payment_intent_id: str) -> CourseAccessGrant | None:
        for grant in self._items.values():
            if grant.payment_intent_id == payment_intent_id:
                return grant
        return None

    def find_by_course_and_student(
        self, course_id: str, student_id: str
    ) -> CourseAccessGrant | None:
        for grant in self._items.values():
            if (
                grant.subject.course_id == course_id
                and grant.subject.student_id == student_id
            ):
                return grant
        return None

    def exists_active_by_course_and_student(
        self, course_id: str, student_id: str
    ) -> bool:
        grant = self.find_by_course_and_student(
            course_id=course_id, student_id=student_id
        )
        return grant is not None and grant.status == AccessStatus.ACTIVE

    def save(self, access_grant: CourseAccessGrant) -> None:
        self._items[access_grant.access_grant_id] = access_grant
