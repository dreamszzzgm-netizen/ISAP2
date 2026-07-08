"""add document review workflow fields

Revision ID: 017
Revises: 016
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("documents", "review_status"):
        op.add_column("documents", sa.Column("review_status", sa.String(50), server_default="needs_review"))
    if not column_exists("documents", "review_comment"):
        op.add_column("documents", sa.Column("review_comment", sa.String(2000)))
    if not column_exists("documents", "reviewed_by"):
        op.add_column("documents", sa.Column("reviewed_by", sa.String(200)))
    if not column_exists("documents", "reviewed_at"):
        op.add_column("documents", sa.Column("reviewed_at", sa.DateTime()))
    if not column_exists("documents", "issued_at"):
        op.add_column("documents", sa.Column("issued_at", sa.DateTime()))


def downgrade() -> None:
    if column_exists("documents", "issued_at"):
        op.drop_column("documents", "issued_at")
    if column_exists("documents", "reviewed_at"):
        op.drop_column("documents", "reviewed_at")
    if column_exists("documents", "reviewed_by"):
        op.drop_column("documents", "reviewed_by")
    if column_exists("documents", "review_comment"):
        op.drop_column("documents", "review_comment")
    if column_exists("documents", "review_status"):
        op.drop_column("documents", "review_status")
