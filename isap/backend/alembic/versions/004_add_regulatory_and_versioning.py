"""Add regulatory_documents, document_versions, calculation_results tables

Revision ID: 004
Revises: 003
Create Date: 2026-06-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regulatory_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="действует"),
        sa.Column("replacement_id", UUID(as_uuid=True), sa.ForeignKey("regulatory_documents.id")),
        sa.Column("last_verified_at", sa.DateTime()),
        sa.Column("verification_source", sa.String(500)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_rd_status", "regulatory_documents", ["status"])
    op.create_index("idx_rd_category", "regulatory_documents", ["category"])

    op.create_table(
        "document_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("input_data", JSONB, nullable=False),
        sa.Column("prompt_version", sa.String(100)),
        sa.Column("template_version", sa.String(100)),
        sa.Column("calculation_results", JSONB, server_default="{}"),
        sa.Column("reviewer_id", UUID(as_uuid=True)),
        sa.Column("reviewer_decision", sa.String(50)),
        sa.Column("reviewer_comments", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_dv_document", "document_versions", ["document_id"])

    op.create_table(
        "calculation_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("method_id", sa.String(100), nullable=False),
        sa.Column("input_params", JSONB, nullable=False),
        sa.Column("results", JSONB, nullable=False),
        sa.Column("validation_status", sa.String(50)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_cr_document", "calculation_results", ["document_id"])
    op.create_index("idx_cr_method", "calculation_results", ["method_id"])


def downgrade() -> None:
    op.drop_table("calculation_results")
    op.drop_table("document_versions")
    op.drop_table("regulatory_documents")
