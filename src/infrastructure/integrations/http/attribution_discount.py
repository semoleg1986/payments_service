"""HTTP адаптер скидок attribution-service."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.application.contracts.ports import DiscountSnapshot
from src.domain.errors import InvariantViolationError


class HttpAttributionDiscountPort:
    """Реализация AttributionDiscountPort через internal API attribution_service."""

    def __init__(
        self, *, base_url: str, service_token: str, timeout_seconds: float = 2.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    def resolve_discount(
        self,
        attribution_token: str | None,
        course_id: str,
        parent_id: str,
    ) -> DiscountSnapshot:
        """Возвращает снимок скидки для расчета final_price."""

        if not attribution_token:
            return DiscountSnapshot(kind="fixed", value=0.0)

        payload = json.dumps(
            {
                "course_id": course_id,
                "referral_token": attribution_token,
                "parent_id": parent_id,
            }
        ).encode("utf-8")

        request = Request(
            f"{self._base_url}/v1/internal/discount/resolve",
            data=payload,
            headers={
                "X-Service-Token": self._service_token,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise InvariantViolationError(
                "Не удалось получить скидку из attribution_service."
            ) from exc
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            raise InvariantViolationError(
                "Не удалось получить скидку из attribution_service."
            ) from exc

        if not bool(response_payload.get("valid", False)):
            return DiscountSnapshot(kind="fixed", value=0.0)

        kind = str(response_payload.get("discount_type", "fixed")).strip().lower()
        if kind not in {"fixed", "percent"}:
            kind = "fixed"

        raw_value = response_payload.get("discount_value")
        if raw_value is None:
            raw_value = (response_payload.get("discount") or {}).get("amount", 0)

        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise InvariantViolationError(
                "attribution_service вернул некорректный discount_value."
            ) from exc

        if value < 0:
            raise InvariantViolationError(
                "attribution_service вернул отрицательный discount_value."
            )

        return DiscountSnapshot(kind=kind, value=value)
