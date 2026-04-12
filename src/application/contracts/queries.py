"""Запросы application-слоя payments_service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetPaymentIntentQuery:
    """Запрос получения PaymentIntent по id."""

    payment_intent_id: str
    actor_id: str
    actor_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GetCourseAccessGrantQuery:
    """Запрос получения CourseAccessGrant по id."""

    access_grant_id: str
    actor_id: str
    actor_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ListPaymentsByParentQuery:
    """Запрос списка платежей родителя."""

    parent_id: str
    actor_id: str
    actor_roles: tuple[str, ...]
