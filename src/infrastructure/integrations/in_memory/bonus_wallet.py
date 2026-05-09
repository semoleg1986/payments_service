"""In-memory adapter for bonus wallet integration."""

from __future__ import annotations

from src.application.contracts.ports import BonusQuoteSnapshot


class InMemoryBonusWalletPort:
    """Test adapter that accepts requested bonus amount as-is."""

    def quote_redeem(
        self,
        *,
        parent_id: str,
        requested_amount: int,
        payment_intent_id: str,
    ) -> BonusQuoteSnapshot:
        return BonusQuoteSnapshot(
            requested_amount=requested_amount,
            allowed_amount=max(requested_amount, 0),
        )

    def commit_redeem(
        self,
        *,
        parent_id: str,
        amount: int,
        payment_intent_id: str,
        idempotency_key: str,
    ) -> None:
        return None

    def revert_redeem(
        self,
        *,
        parent_id: str,
        amount: int,
        payment_intent_id: str,
        idempotency_key: str,
    ) -> None:
        return None
