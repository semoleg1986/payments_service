"""Доменные политики PaymentIntent."""

from __future__ import annotations

from src.domain.errors import AccessDeniedError


def ensure_parent_can_create_intent(actor_id: str, actor_roles: list[str]) -> None:
    """Проверяет, что intent создает родитель или администратор."""

    roles = {role.strip().lower() for role in actor_roles if role.strip()}
    if "parent" not in roles and "admin" not in roles:
        raise AccessDeniedError("Создавать intent может только parent или admin.")
    if not actor_id.strip():
        raise AccessDeniedError("Требуется actor_id.")


def ensure_admin_can_decide(actor_id: str, actor_roles: list[str]) -> None:
    """Проверяет, что решение по оплате принимает администратор."""

    roles = {role.strip().lower() for role in actor_roles if role.strip()}
    if "admin" not in roles:
        raise AccessDeniedError("Подтверждать/отклонять оплату может только admin.")
    if not actor_id.strip():
        raise AccessDeniedError("Требуется actor_id.")
