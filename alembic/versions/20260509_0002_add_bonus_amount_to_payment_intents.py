"""add bonus amount to payment intents

Revision ID: 20260509_0002
Revises: 20260412_0001
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260509_0002"
down_revision: Union[str, Sequence[str], None] = "20260412_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_intents",
        sa.Column(
            "bonus_amount",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("payment_intents", "bonus_amount")
