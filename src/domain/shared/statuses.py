"""Статусы агрегатов платежного домена."""

from __future__ import annotations

from enum import StrEnum


class PaymentStatus(StrEnum):
    """Статус заявки на оплату."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class AccessStatus(StrEnum):
    """Статус доступа к курсу."""

    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
