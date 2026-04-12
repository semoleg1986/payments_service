"""Агрегат CourseAccessGrant."""

from .entity import CourseAccessGrant
from .events import CourseAccessExpired, CourseAccessGranted, CourseAccessRevoked
from .policies import (
    ensure_access_is_active,
    ensure_admin_can_manage_access,
    ensure_no_other_active_access,
)
from .repository import CourseAccessGrantRepository
from .value_objects import AccessSubject, AccessWindow

__all__ = [
    "AccessSubject",
    "AccessWindow",
    "CourseAccessExpired",
    "CourseAccessGrant",
    "CourseAccessGrantRepository",
    "CourseAccessGranted",
    "CourseAccessRevoked",
    "ensure_access_is_active",
    "ensure_admin_can_manage_access",
    "ensure_no_other_active_access",
]
