"""HTTP адаптер commercial_catalog_service."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.application.contracts.ports import OfferSnapshot
from src.domain.errors import InvariantViolationError
from src.interface.http.observability import current_correlation_id


class HttpCommercialCatalogPort:
    """Реализация CommercialCatalogPort через internal API catalog service."""

    def __init__(
        self, *, base_url: str, service_token: str, timeout_seconds: float = 2.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    def get_offer(self, offer_id: str) -> OfferSnapshot | None:
        """Возвращает internal snapshot offer по его идентификатору."""

        url = f"{self._base_url}/internal/v1/offers/{quote(offer_id)}"
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
                "Не удалось получить offer из commercial_catalog_service."
            ) from exc
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            raise InvariantViolationError(
                "Не удалось получить offer из commercial_catalog_service."
            ) from exc

        result_offer_id = str(payload.get("offer_id", "")).strip()
        result_course_id = str(payload.get("course_id", "")).strip()
        if not result_offer_id or not result_course_id:
            raise InvariantViolationError(
                "commercial_catalog_service вернул некорректный offer snapshot."
            )

        is_active = bool(payload.get("is_active", False))
        if not is_active:
            return None

        price_payload = payload.get("price")
        if not isinstance(price_payload, dict):
            raise InvariantViolationError(
                "commercial_catalog_service вернул некорректную цену offer."
            )
        currency = str(price_payload.get("currency", "")).strip()
        if not currency:
            raise InvariantViolationError(
                "commercial_catalog_service вернул некорректную валюту offer."
            )
        try:
            price = float(price_payload.get("sale_price", 0))
        except (TypeError, ValueError) as exc:
            raise InvariantViolationError(
                "commercial_catalog_service вернул некорректную цену offer."
            ) from exc

        return OfferSnapshot(
            offer_id=result_offer_id,
            course_id=result_course_id,
            price=price,
            currency=currency,
        )
