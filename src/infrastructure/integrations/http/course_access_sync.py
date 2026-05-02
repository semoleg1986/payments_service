"""HTTP adapter синхронизации access grant в course_service."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.domain.errors import InvariantViolationError


class HttpCourseAccessSyncPort:
    """Отправляет internal course.access.granted в course_service."""

    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    def sync_course_access_granted(
        self,
        *,
        event_id: str,
        course_id: str,
        student_id: str,
        granted_status: str,
    ) -> None:
        payload = json.dumps(
            {
                "event_id": event_id,
                "course_id": course_id,
                "student_id": student_id,
                "granted_status": granted_status,
            }
        ).encode("utf-8")
        request = Request(
            f"{self._base_url}/internal/v1/access/events/course-access-granted",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Service-Token": self._service_token,
            },
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds):
                return None
        except HTTPError as exc:
            raise InvariantViolationError(
                "Не удалось синхронизировать доступ с course_service."
            ) from exc
        except URLError as exc:
            raise InvariantViolationError(
                "course_service недоступен для синхронизации доступа."
            ) from exc
