"""add agreement_date to emergency_rescue_units

Revision ID: a5c8a2dd1a14
Revises: 019
Create Date: 2026-07-12 15:45:14.266316
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5c8a2dd1a14'
down_revision: Union[str, None] = '019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "emergency_rescue_units",
        sa.Column("agreement_date", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("emergency_rescue_units", "agreement_date")
