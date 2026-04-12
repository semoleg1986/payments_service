"""In-memory адаптер связей parent/student."""

from __future__ import annotations


class InMemoryUserRelationsPort:
    """Тестовый адаптер users_service для локального запуска."""

    def __init__(self) -> None:
        self._relations: dict[str, set[str]] = {
            "parent-1": {"student-1", "student-2"},
            "parent-2": {"student-3"},
        }

    def is_parent_of_student(self, parent_id: str, student_id: str) -> bool:
        students = self._relations.get(parent_id, set())
        return student_id in students
