"""Pydantic-схемы платежных endpoint-ов."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreatePaymentIntentRequest(BaseModel):
    """Запрос на создание intent."""

    payment_intent_id: str | None = None
    parent_id: str
    student_id: str
    offer_id: str
    attribution_token: str | None = None
    bonus_amount: int | None = Field(default=None, ge=0)
    idempotency_key: str | None = None


class ApprovePaymentIntentRequest(BaseModel):
    """Запрос на подтверждение intent."""

    access_grant_id: str | None = None


class RejectPaymentIntentRequest(BaseModel):
    """Запрос на отклонение intent."""

    reason: str | None = Field(default=None, max_length=500)


class PaymentIntentResponse(BaseModel):
    """Ответ с данными intent."""

    payment_intent_id: str
    parent_id: str
    student_id: str
    offer_id: str
    course_id: str
    status: str
    base_price: float
    final_price: float
    bonus_amount: int
    currency: str
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}
