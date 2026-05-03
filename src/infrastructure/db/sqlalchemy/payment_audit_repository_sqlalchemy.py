"""SQLAlchemy репозиторий retained audit evidence."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.application.contracts import AuditEvidenceRecord
from src.infrastructure.db.sqlalchemy.models import PaymentAuditRecordModel
from src.infrastructure.db.sqlalchemy.session_context import get_current_session


class SqlAlchemyPaymentAuditRepository:
    """Append-only хранилище retained audit evidence на SQLAlchemy."""

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

    def append(self, record: AuditEvidenceRecord) -> None:
        with self._session() as session:
            session.add(
                PaymentAuditRecordModel(
                    audit_id=record.audit_id,
                    action=record.action,
                    occurred_at=record.occurred_at,
                    result=record.result,
                    actor_id=record.actor_id,
                    actor_roles=",".join(record.actor_roles),
                    target_type=record.target_type,
                    target_id=record.target_id,
                    reason=record.reason,
                    reason_code=record.reason_code,
                    request_id=record.request_id,
                    correlation_id=record.correlation_id,
                    payment_intent_id=record.payment_intent_id,
                )
            )
            if get_current_session() is None:
                session.commit()

    def list_all(self) -> list[AuditEvidenceRecord]:
        with self._session() as session:
            models = session.scalars(
                select(PaymentAuditRecordModel).order_by(
                    PaymentAuditRecordModel.occurred_at
                )
            ).all()
            return [
                AuditEvidenceRecord(
                    audit_id=model.audit_id,
                    action=model.action,
                    occurred_at=model.occurred_at,
                    result=model.result,
                    actor_id=model.actor_id,
                    actor_roles=tuple(
                        role for role in model.actor_roles.split(",") if role
                    ),
                    target_type=model.target_type,
                    target_id=model.target_id,
                    reason=model.reason,
                    reason_code=model.reason_code,
                    request_id=model.request_id,
                    correlation_id=model.correlation_id,
                    payment_intent_id=model.payment_intent_id,
                )
                for model in models
            ]
