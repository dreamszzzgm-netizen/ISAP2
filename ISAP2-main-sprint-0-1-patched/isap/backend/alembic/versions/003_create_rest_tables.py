"""create_equipment_substances_persons_documents

Revision ID: 003
Revises: 002
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Equipment
    op.create_table(
        "equipment",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazardous_facility_id", UUID(as_uuid=True), sa.ForeignKey("hazardous_facilities.id"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("equipment_type", sa.String(100)),
        sa.Column("serial_number", sa.String(100)),
        sa.Column("manufacturer", sa.String(300)),
        sa.Column("manufacture_year", sa.SmallInteger()),
        sa.Column("specifications", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_eq_facility", "equipment", ["hazardous_facility_id"])

    # Hazardous substances
    op.create_table(
        "hazardous_substances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazardous_facility_id", UUID(as_uuid=True), sa.ForeignKey("hazardous_facilities.id"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("cas_number", sa.String(20)),
        sa.Column("quantity_kg", sa.Numeric(12, 2)),
        sa.Column("threshold_quantity_kg", sa.Numeric(12, 2)),
        sa.Column("hazard_properties", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_hs_facility", "hazardous_substances", ["hazardous_facility_id"])

    # Responsible persons
    op.create_table(
        "responsible_persons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("full_name", sa.String(300), nullable=False),
        sa.Column("position", sa.String(300)),
        sa.Column("role", sa.String(100)),
        sa.Column("phone", sa.String(50)),
        sa.Column("email", sa.String(200)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hazardous_facility_id", UUID(as_uuid=True), sa.ForeignKey("hazardous_facilities.id")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("content_docx", sa.LargeBinary()),
        sa.Column("generation_meta", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_doc_facility", "documents", ["hazardous_facility_id"])
    op.create_index("idx_doc_type", "documents", ["document_type"])


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("responsible_persons")
    op.drop_index("idx_hs_facility")
    op.drop_table("hazardous_substances")
    op.drop_index("idx_eq_facility")
    op.drop_table("equipment")
