"""HTTP адаптер каталога курсов."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.application.contracts.ports import CourseSnapshot
from src.domain.errors import InvariantViolationError
from src.interface.http.observability import current_correlation_id


class HttpCourseCatalogPort:
    """Реализация CourseCatalogPort через internal API course_service."""

    def __init__(
        self, *, base_url: str, service_token: str, timeout_seconds: float = 2.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    def get_course(self, course_id: str) -> CourseSnapshot | None:
        """Возвращает платежный снапшот курса по его идентификатору."""

        url = (
            f"{self._base_url}/internal/v1/access/courses/"
            f"{quote(course_id)}/payment-snapshot"
        )
        request = Request(
            url,
            headers={
                "X-Service-Token": self._service_token,
                **(
                    {"X-Correlation-ID": current_correlation_id()}
                    if current_correlation_id() is not None
                    else {}
                ),
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise InvariantViolationError(
                "Не удалось получить курс из course_service."
            ) from exc
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            raise InvariantViolationError(
                "Не удалось получить курс из course_service."
            ) from exc

        result_course_id = str(payload.get("course_id", "")).strip()
        if not result_course_id:
            raise InvariantViolationError(
                "course_service вернул некорректный payment-snapshot."
            )

        access_ttl_raw = payload.get("access_ttl_days")
        if access_ttl_raw is None:
            access_ttl_days = None
        else:
            try:
                access_ttl_days = int(access_ttl_raw)
            except (TypeError, ValueError) as exc:
                raise InvariantViolationError(
                    "course_service вернул некорректный access_ttl_days."
                ) from exc

        return CourseSnapshot(
            course_id=result_course_id,
            access_ttl_days=access_ttl_days,
        )
