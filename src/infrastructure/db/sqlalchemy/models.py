"""ORM модели payments_service."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.sqlalchemy.base import Base


class PaymentIntentModel(Base):
    """ORM-модель заявки на оплату."""

    __tablename__ = "payment_intents"

    payment_intent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    offer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attribution_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    base_amount: Mapped[float] = mapped_column(Float, nullable=False)
    final_amount: Mapped[float] = mapped_column(Float, nullable=False)
    bonus_amount: Mapped[int] = mapped_column(nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    discount_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    discount_value: Mapped[float] = mapped_column(Float, nullable=False)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CourseAccessGrantModel(Base):
    """ORM-модель доступа к курсу."""

    __tablename__ = "course_access_grants"

    access_grant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payment_intent_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    offer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PaymentAuditRecordModel(Base):
    """ORM-модель retained audit evidence для payments_service."""

    __tablename__ = "payment_audit_records"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor_roles: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    payment_intent_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )


class PaymentOutboxEventModel(Base):
    """ORM-модель persisted outbox для межсервисных side effect."""

    __tablename__ = "payment_outbox_events"
    __table_args__ = (
        UniqueConstraint(
            "aggregate_type",
            "aggregate_id",
            "event_type",
            name="uq_payment_outbox_aggregate_event_type",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
