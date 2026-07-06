"""add regulatory_snapshot to document_versions

Revision ID: 008
Revises: 007
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("document_versions", "regulatory_snapshot"):
        op.add_column("document_versions", sa.Column("regulatory_snapshot", JSONB, server_default="[]"))


def downgrade() -> None:
    if column_exists("document_versions", "regulatory_snapshot"):
        op.drop_column("document_versions", "regulatory_snapshot")
