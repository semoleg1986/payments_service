"""Доменные политики агрегата CourseAccessGrant."""

from __future__ import annotations

from src.domain.errors import AccessDeniedError, InvariantViolationError
from src.domain.shared.statuses import AccessStatus


def ensure_admin_can_manage_access(actor_id: str, actor_roles: list[str]) -> None:
    """Проверяет, что изменением доступов управляет администратор."""

    roles = {role.strip().lower() for role in actor_roles if role.strip()}
    if "admin" not in roles:
        raise AccessDeniedError("Управлять доступом к курсу может только admin.")
    if not actor_id.strip():
        raise AccessDeniedError("Требуется actor_id.")


def ensure_no_other_active_access(
    has_active_access: bool,
    course_id: str,
    student_id: str,
) -> None:
    """Запрещает одновременные active-доступы для одной пары course/student."""

    if has_active_access:
        raise InvariantViolationError(
            "Для пары course_id/student_id уже существует active доступ."
        )
    if not course_id.strip() or not student_id.strip():
        raise InvariantViolationError("course_id и student_id обязательны.")


def ensure_access_is_active(status: AccessStatus) -> None:
    """Проверяет, что доступ сейчас активен."""

    if status != AccessStatus.ACTIVE:
        raise InvariantViolationError("Операция доступна только для active доступа.")
