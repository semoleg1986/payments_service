"""Pydantic-схемы платежных endpoint-ов."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.payments.payment_intent.value_objects import PaymentIntentRejectReason
from src.interface.http.v1.schemas.access import CourseAccessGrantResponse


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

    reason: PaymentIntentRejectReason | None = None


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
    rejected_reason: str | None = None
    review_state: str
    recommended_reject_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


class CheckoutActionsResponse(BaseModel):
    """Доступные действия для checkout UI."""

    can_create_payment_intent: bool
    can_retry_payment: bool
    next_action: str
    resume_payment_intent_id: str | None = None

    model_config = {"from_attributes": True}


class CheckoutOfferResponse(BaseModel):
    """Явный offer block в checkout-state."""

    offer_id: str
    course_id: str
    base_price: float
    final_price: float
    bonus_amount: int
    currency: str
    source: str
    payment_intent_id: str | None = None
    access_grant_id: str | None = None

    model_config = {"from_attributes": True}


class CheckoutStateResponse(BaseModel):
    """Read model checkout-state для parent UI."""

    parent_id: str
    student_id: str
    course_id: str
    checkout_state: str
    selected_offer: CheckoutOfferResponse | None = None
    purchased_offer: CheckoutOfferResponse | None = None
    latest_payment_intent: PaymentIntentResponse | None = None
    access_grant: CourseAccessGrantResponse | None = None
    available_actions: CheckoutActionsResponse

    model_config = {"from_attributes": True}
