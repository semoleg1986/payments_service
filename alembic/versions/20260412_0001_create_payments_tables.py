"""create payments tables

Revision ID: 20260412_0001
Revises:
Create Date: 2026-04-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260412_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_intents",
        sa.Column("payment_intent_id", sa.String(length=64), primary_key=True),
        sa.Column("parent_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("attribution_token", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("base_amount", sa.Float(), nullable=False),
        sa.Column("final_amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("discount_kind", sa.String(length=16), nullable=False),
        sa.Column("discount_value", sa.Float(), nullable=False),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_payment_intents_parent_id", "payment_intents", ["parent_id"], unique=False
    )
    op.create_index(
        "ix_payment_intents_student_id", "payment_intents", ["student_id"], unique=False
    )
    op.create_index(
        "ix_payment_intents_course_id", "payment_intents", ["course_id"], unique=False
    )
    op.create_index(
        "ix_payment_intents_idempotency_key",
        "payment_intents",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_payment_intents_status", "payment_intents", ["status"], unique=False
    )

    op.create_table(
        "course_access_grants",
        sa.Column("access_grant_id", sa.String(length=64), primary_key=True),
        sa.Column("payment_intent_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=64), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_course_access_grants_payment_intent_id",
        "course_access_grants",
        ["payment_intent_id"],
        unique=True,
    )
    op.create_index(
        "ix_course_access_grants_course_id",
        "course_access_grants",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        "ix_course_access_grants_student_id",
        "course_access_grants",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        "ix_course_access_grants_status",
        "course_access_grants",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_course_access_grants_status", table_name="course_access_grants")
    op.drop_index(
        "ix_course_access_grants_student_id", table_name="course_access_grants"
    )
    op.drop_index(
        "ix_course_access_grants_course_id", table_name="course_access_grants"
    )
    op.drop_index(
        "ix_course_access_grants_payment_intent_id", table_name="course_access_grants"
    )
    op.drop_table("course_access_grants")

    op.drop_index("ix_payment_intents_status", table_name="payment_intents")
    op.drop_index("ix_payment_intents_idempotency_key", table_name="payment_intents")
    op.drop_index("ix_payment_intents_course_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_student_id", table_name="payment_intents")
    op.drop_index("ix_payment_intents_parent_id", table_name="payment_intents")
    op.drop_table("payment_intents")
