"""HTTP адаптер связей parent/student."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.domain.errors import InvariantViolationError


class HttpUserRelationsPort:
    """Реализация UserRelationsPort через internal API users_service."""

    def __init__(
        self, *, base_url: str, service_token: str, timeout_seconds: float = 2.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    def is_parent_of_student(self, parent_id: str, student_id: str) -> bool:
        """Проверяет активную связь parent и student через users_service."""

        url = (
            f"{self._base_url}/internal/v1/parent-students/"
            f"{quote(parent_id)}/{quote(student_id)}"
        )
        request = Request(
            url,
            headers={"X-Service-Token": self._service_token},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise InvariantViolationError(
                "Не удалось проверить связь parent/student в users_service."
            ) from exc
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            raise InvariantViolationError(
                "Не удалось проверить связь parent/student в users_service."
            ) from exc

        return bool(payload.get("has_relation", False))

