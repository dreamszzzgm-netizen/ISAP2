"""add ai_review and regulatory_snapshot fields to document_versions

Revision ID: 012
Revises: 011
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "012"
down_revision = "011"
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
    if not column_exists("document_versions", "ai_review_confidence"):
        op.add_column("document_versions", sa.Column("ai_review_confidence", sa.Numeric(3, 2)))
    if not column_exists("document_versions", "ai_review_decision"):
        op.add_column("document_versions", sa.Column("ai_review_decision", sa.String(50)))
    if not column_exists("document_versions", "ai_review_items"):
        op.add_column("document_versions", sa.Column("ai_review_items", JSONB, server_default="[]"))
    if not column_exists("document_versions", "ai_review_summary"):
        op.add_column("document_versions", sa.Column("ai_review_summary", sa.Text()))


def downgrade() -> None:
    if column_exists("document_versions", "ai_review_summary"):
        op.drop_column("document_versions", "ai_review_summary")
    if column_exists("document_versions", "ai_review_items"):
        op.drop_column("document_versions", "ai_review_items")
    if column_exists("document_versions", "ai_review_decision"):
        op.drop_column("document_versions", "ai_review_decision")
    if column_exists("document_versions", "ai_review_confidence"):
        op.drop_column("document_versions", "ai_review_confidence")
    if column_exists("document_versions", "regulatory_snapshot"):
        op.drop_column("document_versions", "regulatory_snapshot")
