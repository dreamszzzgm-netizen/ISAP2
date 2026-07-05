"""add regeneration_count to documents

Revision ID: 014
Revises: 013
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("documents", "regeneration_count"):
        op.add_column("documents", sa.Column("regeneration_count", sa.Integer(), server_default="0"))


def downgrade() -> None:
    if column_exists("documents", "regeneration_count"):
        op.drop_column("documents", "regeneration_count")
