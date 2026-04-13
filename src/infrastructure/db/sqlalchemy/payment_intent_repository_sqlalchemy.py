"""SQLAlchemy репозиторий PaymentIntent."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, sessionmaker

from src.domain.payments.payment_intent.entity import PaymentIntent
from src.domain.payments.payment_intent.value_objects import (
    Discount,
    Money,
    PaymentContext,
)
from src.domain.shared.entity import EntityMeta
from src.domain.shared.statuses import PaymentStatus
from src.infrastructure.db.sqlalchemy.models import PaymentIntentModel
from src.infrastructure.db.sqlalchemy.session_context import get_current_session


class SqlAlchemyPaymentIntentRepository:
    """Репозиторий заявок оплаты на SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _session(self) -> Session:
        current = get_current_session()
        if current is not None:
            yield current
            return
        with self._session_factory() as session:
            yield session

    def get(self, payment_intent_id: str) -> PaymentIntent | None:
        with self._session() as session:
            model = session.get(PaymentIntentModel, payment_intent_id)
            return self._to_entity(model) if model else None

    def get_by_idempotency_key(
        self,
        parent_id: str,
        idempotency_key: str,
    ) -> PaymentIntent | None:
        with self._session() as session:
            model = session.scalar(
                select(PaymentIntentModel).where(
                    and_(
                        PaymentIntentModel.parent_id == parent_id,
                        PaymentIntentModel.idempotency_key == idempotency_key,
                    )
                )
            )
            return self._to_entity(model) if model else None

    def list_by_parent(self, parent_id: str) -> list[PaymentIntent]:
        with self._session() as session:
            models = session.scalars(
                select(PaymentIntentModel).where(
                    PaymentIntentModel.parent_id == parent_id
                )
            ).all()
            return [self._to_entity(item) for item in models]

    def save(self, intent: PaymentIntent) -> None:
        with self._session() as session:
            model = session.get(PaymentIntentModel, intent.payment_intent_id)
            if model is None:
                model = PaymentIntentModel(payment_intent_id=intent.payment_intent_id)
                session.add(model)
            self._fill_model(model, intent)
            if get_current_session() is None:
                session.commit()

    @staticmethod
    def _fill_model(model: PaymentIntentModel, intent: PaymentIntent) -> None:
        model.parent_id = intent.context.parent_id
        model.student_id = intent.context.student_id
        model.course_id = intent.context.course_id
        model.attribution_token = intent.context.attribution_token
        model.idempotency_key = intent.context.idempotency_key
        model.expires_at = intent.context.expires_at
        model.status = intent.status.value
        model.base_amount = float(intent.base_price.amount)
        model.final_amount = float(intent.final_price.amount)
        model.currency = intent.final_price.currency
        model.discount_kind = intent.discount.kind
        model.discount_value = float(intent.discount.value)
        model.rejected_reason = intent.rejected_reason
        model.approved_at = intent.approved_at
        model.approved_by = intent.approved_by
        model.rejected_at = intent.rejected_at
        model.rejected_by = intent.rejected_by
        model.version = intent.meta.version
        model.created_at = intent.meta.created_at
        model.created_by = intent.meta.created_by
        model.updated_at = intent.meta.updated_at
        model.updated_by = intent.meta.updated_by
        model.archived_at = intent.meta.archived_at
        model.archived_by = intent.meta.archived_by

    @staticmethod
    def _to_entity(model: PaymentIntentModel) -> PaymentIntent:
        return PaymentIntent(
            payment_intent_id=model.payment_intent_id,
            context=PaymentContext(
                parent_id=model.parent_id,
                student_id=model.student_id,
                course_id=model.course_id,
                attribution_token=model.attribution_token,
                idempotency_key=model.idempotency_key,
                expires_at=model.expires_at,
            ),
            base_price=Money(amount=float(model.base_amount), currency=model.currency),
            discount=Discount(
                kind=model.discount_kind, value=float(model.discount_value)
            ),
            final_price=Money(
                amount=float(model.final_amount), currency=model.currency
            ),
            status=PaymentStatus(model.status),
            meta=EntityMeta(
                version=model.version,
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                archived_at=model.archived_at,
                archived_by=model.archived_by,
            ),
            rejected_reason=model.rejected_reason,
            approved_at=model.approved_at,
            approved_by=model.approved_by,
            rejected_at=model.rejected_at,
            rejected_by=model.rejected_by,
            events=[],
        )
