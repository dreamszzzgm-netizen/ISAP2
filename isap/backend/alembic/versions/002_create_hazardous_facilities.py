"""create_hazardous_facilities

Revision ID: 002
Revises: 001
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hazardous_facilities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("reg_number", sa.String(50), unique=True),
        sa.Column("hazard_class", sa.SmallInteger()),
        sa.Column("facility_type", sa.String(100)),
        sa.Column("address", sa.Text()),
        sa.Column("properties", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_hf_organization", "hazardous_facilities", ["organization_id"])
    op.create_index("idx_hf_properties", "hazardous_facilities", ["properties"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("idx_hf_properties")
    op.drop_index("idx_hf_organization")
    op.drop_table("hazardous_facilities")
