"""add opo_details for Сведения об ОПО form

Revision ID: 013
Revises: 012
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def table_exists(table):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=:table)"
    ), {"table": table})
    return result.scalar()


def upgrade() -> None:
    if not table_exists("opo_details"):
        op.create_table(
            "opo_details",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("hazardous_facilities.id"), unique=True, nullable=False),
            sa.Column("form_data", JSONB, server_default="{}"),
            sa.Column("total_amount", sa.Numeric(10, 3), server_default="0"),
            sa.Column("applicant_type", sa.String(20), server_default="legal"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
        )
        op.create_index("idx_opo_details_facility", "opo_details", ["facility_id"])


def downgrade() -> None:
    if table_exists("opo_details"):
        op.drop_index("idx_opo_details_facility")
        op.drop_table("opo_details")
