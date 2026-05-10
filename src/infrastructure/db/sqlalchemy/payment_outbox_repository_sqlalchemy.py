"""SQLAlchemy репозиторий persisted outbox событий."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.application.contracts import (
    OutboxEventRecord,
    OutboxEventStatus,
    OutboxEventType,
)
from src.infrastructure.db.sqlalchemy.models import PaymentOutboxEventModel
from src.infrastructure.db.sqlalchemy.session_context import get_current_session


class SqlAlchemyPaymentOutboxRepository:
    """Persisted outbox-хранилище на SQLAlchemy."""

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

    def add(self, event: OutboxEventRecord) -> None:
        with self._session() as session:
            session.add(self._to_model(event))
            if get_current_session() is None:
                session.commit()

    def save(self, event: OutboxEventRecord) -> None:
        with self._session() as session:
            model = session.get(PaymentOutboxEventModel, event.event_id)
            if model is None:
                session.add(self._to_model(event))
            else:
                self._fill_model(model, event)
            if get_current_session() is None:
                session.commit()

    def list_pending(self, *, limit: int = 100) -> list[OutboxEventRecord]:
        with self._session() as session:
            models = session.scalars(
                select(PaymentOutboxEventModel)
                .where(
                    PaymentOutboxEventModel.status == OutboxEventStatus.PENDING.value
                )
                .order_by(PaymentOutboxEventModel.created_at)
                .limit(limit)
            ).all()
            return [self._to_entity(item) for item in models]

    def list_pending_by_aggregate(
        self, *, aggregate_id: str
    ) -> list[OutboxEventRecord]:
        with self._session() as session:
            models = session.scalars(
                select(PaymentOutboxEventModel)
                .where(
                    PaymentOutboxEventModel.aggregate_id == aggregate_id,
                    PaymentOutboxEventModel.status == OutboxEventStatus.PENDING.value,
                )
                .order_by(PaymentOutboxEventModel.created_at)
            ).all()
            return [self._to_entity(item) for item in models]

    def count_pending(self) -> int:
        with self._session() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(PaymentOutboxEventModel)
                    .where(
                        PaymentOutboxEventModel.status
                        == OutboxEventStatus.PENDING.value
                    )
                )
                or 0
            )

    def oldest_pending_created_at(self):
        with self._session() as session:
            return session.scalar(
                select(func.min(PaymentOutboxEventModel.created_at)).where(
                    PaymentOutboxEventModel.status == OutboxEventStatus.PENDING.value
                )
            )

    @staticmethod
    def _to_model(event: OutboxEventRecord) -> PaymentOutboxEventModel:
        return PaymentOutboxEventModel(
            event_id=event.event_id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type.value,
            payload_json=event.payload_json,
            status=event.status.value,
            attempt_count=event.attempt_count,
            available_at=event.available_at,
            created_at=event.created_at,
            processed_at=event.processed_at,
            last_error=event.last_error,
        )

    @staticmethod
    def _fill_model(model: PaymentOutboxEventModel, event: OutboxEventRecord) -> None:
        model.aggregate_type = event.aggregate_type
        model.aggregate_id = event.aggregate_id
        model.event_type = event.event_type.value
        model.payload_json = event.payload_json
        model.status = event.status.value
        model.attempt_count = event.attempt_count
        model.available_at = event.available_at
        model.created_at = event.created_at
        model.processed_at = event.processed_at
        model.last_error = event.last_error

    @staticmethod
    def _to_entity(model: PaymentOutboxEventModel) -> OutboxEventRecord:
        return OutboxEventRecord(
            event_id=model.event_id,
            aggregate_type=model.aggregate_type,
            aggregate_id=model.aggregate_id,
            event_type=OutboxEventType(model.event_type),
            payload_json=model.payload_json,
            status=OutboxEventStatus(model.status),
            attempt_count=int(model.attempt_count),
            available_at=model.available_at,
            created_at=model.created_at,
            processed_at=model.processed_at,
            last_error=model.last_error,
        )
