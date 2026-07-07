"""add version column to documents

Revision ID: 016
Revises: 015
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("documents", "version"):
        op.add_column("documents", sa.Column("version", sa.Integer(), server_default="1"))


def downgrade() -> None:
    if column_exists("documents", "version"):
        op.drop_column("documents", "version")
