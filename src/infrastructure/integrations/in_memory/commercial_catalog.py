"""In-memory адаптер commercial_catalog_service."""

from __future__ import annotations

from src.application.contracts.ports import OfferSnapshot


class InMemoryCommercialCatalogPort:
    """Тестовый адаптер commercial catalog для локального запуска."""

    def __init__(self) -> None:
        self._offers: dict[str, OfferSnapshot] = {
            "course-1-standard": OfferSnapshot(
                offer_id="course-1-standard",
                course_id="course-1",
                price=120.0,
                currency="USD",
            ),
            "course-2-standard": OfferSnapshot(
                offer_id="course-2-standard",
                course_id="course-2",
                price=0.0,
                currency="USD",
            ),
        }

    def get_offer(self, offer_id: str) -> OfferSnapshot | None:
        return self._offers.get(offer_id)
