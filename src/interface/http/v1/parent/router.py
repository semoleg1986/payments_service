"""Parent endpoint-ы платежного сервиса."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.application.contracts import (
    ApplicationFacade,
    CancelPaymentIntentCommand,
    CreatePaymentIntentCommand,
    GetPaymentIntentQuery,
    ListPaymentsByParentQuery,
)
from src.interface.http.common.actor import HttpActor, get_http_actor
from src.interface.http.common.rate_limit import enforce_parent_create_rate_limit
from src.interface.http.observability import increment_counter
from src.interface.http.v1.schemas.payment import (
    CreatePaymentIntentRequest,
    PaymentIntentResponse,
)
from src.interface.http.wiring import get_facade

router = APIRouter(prefix="/v1/parent/payments", tags=["parent-payments"])


@router.post("/intents", response_model=PaymentIntentResponse, status_code=201)
def create_payment_intent(
    body: CreatePaymentIntentRequest,
    request: Request,
    _: None = Depends(enforce_parent_create_rate_limit),
    actor: HttpActor = Depends(get_http_actor),
    facade: ApplicationFacade = Depends(get_facade),
) -> PaymentIntentResponse:
    """Создает intent на оплату offer."""

    result = facade.create_payment_intent(
        CreatePaymentIntentCommand(
            payment_intent_id=body.payment_intent_id or "",
            parent_id=body.parent_id,
            student_id=body.student_id,
            offer_id=body.offer_id,
            attribution_token=body.attribution_token,
            bonus_amount=body.bonus_amount,
            idempotency_key=body.idempotency_key,
            actor_id=actor.actor_id,
            actor_roles=actor.roles,
        )
    )
    increment_counter(
        "payment_intents_created_total",
        "Total created payment intents.",
        result="success",
    )
    return PaymentIntentResponse.model_validate(result)


@router.get("/intents/{payment_intent_id}", response_model=PaymentIntentResponse)
def get_payment_intent(
    payment_intent_id: str,
    actor: HttpActor = Depends(get_http_actor),
    facade: ApplicationFacade = Depends(get_facade),
) -> PaymentIntentResponse:
    """Возвращает intent по id."""

    result = facade.get_payment_intent(
        GetPaymentIntentQuery(
            payment_intent_id=payment_intent_id,
            actor_id=actor.actor_id,
            actor_roles=actor.roles,
        )
    )
    return PaymentIntentResponse.model_validate(result)


@router.get("/parents/{parent_id}", response_model=list[PaymentIntentResponse])
def list_payments_by_parent(
    parent_id: str,
    actor: HttpActor = Depends(get_http_actor),
    facade: ApplicationFacade = Depends(get_facade),
) -> list[PaymentIntentResponse]:
    """Возвращает платежи родителя."""

    result = facade.list_payments_by_parent(
        ListPaymentsByParentQuery(
            parent_id=parent_id,
            actor_id=actor.actor_id,
            actor_roles=actor.roles,
        )
    )
    return [PaymentIntentResponse.model_validate(x) for x in result]


@router.post(
    "/intents/{payment_intent_id}/cancel", response_model=PaymentIntentResponse
)
def cancel_payment_intent(
    payment_intent_id: str,
    actor: HttpActor = Depends(get_http_actor),
    facade: ApplicationFacade = Depends(get_facade),
) -> PaymentIntentResponse:
    """Отменяет intent владельцем-parent."""

    result = facade.cancel_payment_intent(
        CancelPaymentIntentCommand(
            payment_intent_id=payment_intent_id,
            actor_id=actor.actor_id,
            actor_roles=actor.roles,
        )
    )
    return PaymentIntentResponse.model_validate(result)
