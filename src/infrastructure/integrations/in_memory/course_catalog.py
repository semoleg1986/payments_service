"""In-memory адаптер каталога курсов."""

from __future__ import annotations

from src.application.contracts.ports import CourseSnapshot


class InMemoryCourseCatalogPort:
    """Тестовый адаптер course_service для локального запуска."""

    def __init__(self) -> None:
        self._courses: dict[str, CourseSnapshot] = {
            "course-1": CourseSnapshot(
                course_id="course-1",
                price=120.0,
                currency="USD",
                access_ttl_days=30,
            ),
            "course-2": CourseSnapshot(
                course_id="course-2",
                price=0.0,
                currency="USD",
                access_ttl_days=None,
            ),
        }

    def get_course(self, course_id: str) -> CourseSnapshot | None:
        return self._courses.get(course_id)
