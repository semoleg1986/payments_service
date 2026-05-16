"""add offer id to payments and access grants

Revision ID: 20260517_0004
Revises: 20260510_0003
Create Date: 2026-05-17
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260517_0004"
down_revision: Union[str, Sequence[str], None] = "20260510_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_intents",
        sa.Column("offer_id", sa.String(length=64), nullable=True),
    )
    op.execute("UPDATE payment_intents SET offer_id = course_id WHERE offer_id IS NULL")
    op.alter_column("payment_intents", "offer_id", nullable=False)
    op.create_index(
        "ix_payment_intents_offer_id", "payment_intents", ["offer_id"], unique=False
    )

    op.add_column(
        "course_access_grants",
        sa.Column("offer_id", sa.String(length=64), nullable=True),
    )
    op.execute(
        "UPDATE course_access_grants SET offer_id = course_id WHERE offer_id IS NULL"
    )
    op.alter_column("course_access_grants", "offer_id", nullable=False)
    op.create_index(
        "ix_course_access_grants_offer_id",
        "course_access_grants",
        ["offer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_course_access_grants_offer_id", table_name="course_access_grants")
    op.drop_column("course_access_grants", "offer_id")

    op.drop_index("ix_payment_intents_offer_id", table_name="payment_intents")
    op.drop_column("payment_intents", "offer_id")
