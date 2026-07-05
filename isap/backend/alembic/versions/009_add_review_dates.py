"""add review dates to documents

Revision ID: 009
Revises: 008
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("documents", "submitted_at"):
        op.add_column("documents", sa.Column("submitted_at", sa.DateTime()))
    if not column_exists("documents", "approved_at"):
        op.add_column("documents", sa.Column("approved_at", sa.DateTime()))
    if not column_exists("documents", "rejected_at"):
        op.add_column("documents", sa.Column("rejected_at", sa.DateTime()))
    if not column_exists("documents", "review_date"):
        op.add_column("documents", sa.Column("review_date", sa.DateTime()))


def downgrade() -> None:
    if column_exists("documents", "review_date"):
        op.drop_column("documents", "review_date")
    if column_exists("documents", "rejected_at"):
        op.drop_column("documents", "rejected_at")
    if column_exists("documents", "approved_at"):
        op.drop_column("documents", "approved_at")
    if column_exists("documents", "submitted_at"):
        op.drop_column("documents", "submitted_at")
