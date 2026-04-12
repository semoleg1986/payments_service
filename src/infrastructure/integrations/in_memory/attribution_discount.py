"""In-memory адаптер скидок attribution."""

from __future__ import annotations

from src.application.contracts.ports import DiscountSnapshot


class InMemoryAttributionDiscountPort:
    """Тестовый адаптер attribution_service для локального запуска."""

    def resolve_discount(
        self,
        attribution_token: str | None,
        course_id: str,
        parent_id: str,
    ) -> DiscountSnapshot:
        if attribution_token and attribution_token.startswith("promo10"):
            return DiscountSnapshot(kind="percent", value=10.0)
        if attribution_token and attribution_token.startswith("promo50"):
            return DiscountSnapshot(kind="fixed", value=50.0)
        return DiscountSnapshot(kind="none", value=0.0)
