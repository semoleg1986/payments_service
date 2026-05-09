"""HTTP adapter for bonus_wallet_service."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.application.contracts.ports import BonusQuoteSnapshot
from src.domain.errors import InvariantViolationError
from src.interface.http.observability import current_correlation_id


class HttpBonusWalletPort:
    """Calls internal bonus_wallet_service endpoints."""

    def __init__(
        self, *, base_url: str, service_token: str, timeout_seconds: float = 2.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    def quote_redeem(
        self,
        *,
        parent_id: str,
        requested_amount: int,
        payment_intent_id: str,
    ) -> BonusQuoteSnapshot:
        payload = self._request(
            "/internal/v1/bonus/redemptions/quote",
            {
                "parent_id": parent_id,
                "requested_amount": requested_amount,
                "payment_intent_id": payment_intent_id,
            },
        )
        try:
            allowed_amount = int(payload.get("allowed_amount", 0))
            raw_requested = payload.get("requested_amount", requested_amount)
            normalized_requested = int(raw_requested)
        except (TypeError, ValueError) as exc:
            raise InvariantViolationError(
                "bonus_wallet_service вернул некорректный redeem quote."
            ) from exc
        if allowed_amount < 0:
            raise InvariantViolationError(
                "bonus_wallet_service вернул отрицательный allowed_amount."
            )
        return BonusQuoteSnapshot(
            requested_amount=normalized_requested,
            allowed_amount=allowed_amount,
        )

    def commit_redeem(
        self,
        *,
        parent_id: str,
        amount: int,
        payment_intent_id: str,
        idempotency_key: str,
    ) -> None:
        self._request(
            "/internal/v1/bonus/redemptions/commit",
            {
                "parent_id": parent_id,
                "amount": amount,
                "payment_intent_id": payment_intent_id,
                "idempotency_key": idempotency_key,
            },
        )

    def revert_redeem(
        self,
        *,
        parent_id: str,
        amount: int,
        payment_intent_id: str,
        idempotency_key: str,
    ) -> None:
        self._request(
            "/internal/v1/bonus/redemptions/revert",
            {
                "parent_id": parent_id,
                "amount": amount,
                "payment_intent_id": payment_intent_id,
                "idempotency_key": idempotency_key,
            },
        )

    def _request(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        request = Request(
            f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "X-Service-Token": self._service_token,
                "Content-Type": "application/json",
                **(
                    {"X-Correlation-ID": current_correlation_id()}
                    if current_correlation_id() is not None
                    else {}
                ),
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise InvariantViolationError(
                "Не удалось выполнить запрос в bonus_wallet_service."
            ) from exc
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            raise InvariantViolationError(
                "Не удалось выполнить запрос в bonus_wallet_service."
            ) from exc
