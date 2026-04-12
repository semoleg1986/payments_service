"""Ошибки доменного слоя payments_service."""


class DomainError(Exception):
    """Базовая ошибка доменного слоя."""


class InvariantViolationError(DomainError):
    """Ошибка нарушения доменного инварианта."""


class AccessDeniedError(DomainError):
    """Ошибка доменной политики доступа."""


class NotFoundError(DomainError):
    """Ошибка отсутствия сущности в домене."""
