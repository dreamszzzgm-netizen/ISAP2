"""add pasf_documents table

Revision ID: 019
Revises: 018
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def table_exists(table: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=:table)"),
        {"table": table},
    )
    return bool(result.scalar())


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return bool(result.scalar())


def index_exists(idx_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname=:idx)"),
        {"idx": idx_name},
    )
    return bool(result.scalar())


def upgrade() -> None:
    if not table_exists("pasf_documents"):
        op.create_table(
            "pasf_documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("pasf_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("emergency_rescue_units.id", ondelete="CASCADE"),
                      nullable=False),
            sa.Column("document_type", sa.String(50), nullable=False, server_default="certificate"),
            sa.Column("document_number", sa.String(200)),
            sa.Column("title", sa.String(500)),
            sa.Column("issued_at", sa.Date()),
            sa.Column("valid_until", sa.Date()),
            sa.Column("file_path", sa.String(1000)),
            sa.Column("file_name", sa.String(500)),
            sa.Column("file_size", sa.Integer()),
            sa.Column("mime_type", sa.String(100)),
            sa.Column("checksum_sha256", sa.String(64)),
            sa.Column("status", sa.String(20), server_default="active"),
            sa.Column("verified_at", sa.DateTime()),
            sa.Column("verified_by", sa.String(200)),
            sa.Column("notes", sa.Text()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )

    # Indexes
    if not index_exists("ix_pasf_documents_pasf_id"):
        op.create_index("ix_pasf_documents_pasf_id", "pasf_documents", ["pasf_id"])
    if not index_exists("ix_pasf_documents_document_type"):
        op.create_index("ix_pasf_documents_document_type", "pasf_documents", ["document_type"])
    if not index_exists("ix_pasf_documents_valid_until"):
        op.create_index("ix_pasf_documents_valid_until", "pasf_documents", ["valid_until"])


def downgrade() -> None:
    if table_exists("pasf_documents"):
        op.drop_table("pasf_documents")
