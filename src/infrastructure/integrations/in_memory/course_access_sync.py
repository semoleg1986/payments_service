"""In-memory course access sync adapter."""

from __future__ import annotations


class InMemoryCourseAccessSyncPort:
    """No-op адаптер синхронизации course access для тестов/локального режима."""

    def sync_course_access_granted(
        self,
        *,
        event_id: str,
        course_id: str,
        student_id: str,
        granted_status: str,
    ) -> None:
        return None
