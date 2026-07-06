"""add content_docx to document_versions for version restore

Revision ID: 011
Revises: 010
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("document_versions", "content_docx"):
        op.add_column("document_versions", sa.Column("content_docx", sa.LargeBinary()))


def downgrade() -> None:
    if column_exists("document_versions", "content_docx"):
        op.drop_column("document_versions", "content_docx")
