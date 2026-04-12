"""Pydantic-схемы доступа к курсу."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CourseAccessGrantResponse(BaseModel):
    """Ответ с данными доступа к курсу."""

    access_grant_id: str
    payment_intent_id: str
    course_id: str
    student_id: str
    status: str
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


class AccessCheckResponse(BaseModel):
    """Ответ проверки доступа ученика к курсу."""

    has_access: bool
    course_id: str
    student_id: str
    access_grant_id: str | None = None
    status: str | None = None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}
