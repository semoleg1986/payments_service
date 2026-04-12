"""Admin endpoint-ы платежного сервиса."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.application.contracts import (
    ApplicationFacade,
    ApprovePaymentIntentCommand,
    RejectPaymentIntentCommand,
)
from src.interface.http.common.actor import HttpActor, get_http_actor
from src.interface.http.v1.schemas.access import CourseAccessGrantResponse
from src.interface.http.v1.schemas.payment import (
    ApprovePaymentIntentRequest,
    PaymentIntentResponse,
    RejectPaymentIntentRequest,
)
from src.interface.http.wiring import get_facade

router = APIRouter(prefix="/v1/admin/payments", tags=["admin-payments"])


@router.post(
    "/{payment_intent_id}/approve",
    response_model=CourseAccessGrantResponse,
)
def approve_payment_intent(
    payment_intent_id: str,
    body: ApprovePaymentIntentRequest,
    actor: HttpActor = Depends(get_http_actor),
    facade: ApplicationFacade = Depends(get_facade),
) -> CourseAccessGrantResponse:
    """Подтверждает intent и выдает доступ."""

    result = facade.approve_payment_intent(
        ApprovePaymentIntentCommand(
            payment_intent_id=payment_intent_id,
            admin_id=actor.actor_id,
            admin_roles=actor.roles,
            access_grant_id=body.access_grant_id or "",
        )
    )
    return CourseAccessGrantResponse.model_validate(result)


@router.post("/{payment_intent_id}/reject", response_model=PaymentIntentResponse)
def reject_payment_intent(
    payment_intent_id: str,
    body: RejectPaymentIntentRequest,
    actor: HttpActor = Depends(get_http_actor),
    facade: ApplicationFacade = Depends(get_facade),
) -> PaymentIntentResponse:
    """Отклоняет intent."""

    result = facade.reject_payment_intent(
        RejectPaymentIntentCommand(
            payment_intent_id=payment_intent_id,
            admin_id=actor.actor_id,
            admin_roles=actor.roles,
            reason=body.reason,
        )
    )
    return PaymentIntentResponse.model_validate(result)
