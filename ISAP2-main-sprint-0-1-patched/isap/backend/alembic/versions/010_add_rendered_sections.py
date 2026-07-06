"""add rendered_sections to documents for partial regeneration

Revision ID: 010
Revises: 009
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("documents", "rendered_sections"):
        op.add_column("documents", sa.Column("rendered_sections", JSONB, server_default="{}"))


def downgrade() -> None:
    if column_exists("documents", "rendered_sections"):
        op.drop_column("documents", "rendered_sections")
