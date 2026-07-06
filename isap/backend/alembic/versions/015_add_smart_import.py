"""add smart import center

Revision ID: 015
Revises: 014
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def table_exists(table: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=:table)"),
        {"table": table},
    )
    return bool(result.scalar())


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())

    if not table_exists("import_jobs"):
        op.create_table(
            "import_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("import_type", sa.String(length=100), nullable=False),
            sa.Column("filename", sa.String(length=500), nullable=False),
            sa.Column("status", sa.String(length=50), server_default="preview"),
            sa.Column("header_mapping", jsonb, server_default="{}"),
            sa.Column("total_rows", sa.Integer(), server_default="0"),
            sa.Column("created_rows", sa.Integer(), server_default="0"),
            sa.Column("updated_rows", sa.Integer(), server_default="0"),
            sa.Column("skipped_rows", sa.Integer(), server_default="0"),
            sa.Column("error_rows", sa.Integer(), server_default="0"),
            sa.Column("warning_rows", sa.Integer(), server_default="0"),
            sa.Column("report", jsonb, server_default="{}"),
            sa.Column("created_by", sa.String(length=200)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("finished_at", sa.DateTime()),
        )

    if not table_exists("import_rows"):
        op.create_table(
            "import_rows",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("import_jobs.id"), nullable=False),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("raw_data", jsonb, server_default="{}"),
            sa.Column("mapped_data", jsonb, server_default="{}"),
            sa.Column("normalized_data", jsonb, server_default="{}"),
            sa.Column("status", sa.String(length=50), server_default="pending"),
            sa.Column("errors", jsonb, server_default="[]"),
            sa.Column("warnings", jsonb, server_default="[]"),
            sa.Column("duplicate_candidates", jsonb, server_default="[]"),
            sa.Column("action", sa.String(length=50), server_default="create"),
            sa.Column("created_at", sa.DateTime()),
        )

    if not table_exists("emergency_rescue_units"):
        op.create_table(
            "emergency_rescue_units",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(length=500), nullable=False),
            sa.Column("short_name", sa.String(length=200)),
            sa.Column("legal_address", sa.String(length=500)),
            sa.Column("actual_address", sa.String(length=500)),
            sa.Column("dispatch_phone", sa.String(length=100)),
            sa.Column("email", sa.String(length=200)),
            sa.Column("manager_name", sa.String(length=300)),
            sa.Column("certificate_number", sa.String(length=100)),
            sa.Column("certificate_date", sa.String(length=50)),
            sa.Column("certificate_valid_until", sa.String(length=50)),
            sa.Column("permitted_work_types", jsonb, server_default="[]"),
            sa.Column("equipment_passport", jsonb, server_default="[]"),
            sa.Column("staff_count", sa.String(length=50)),
            sa.Column("readiness_mode", sa.String(length=200)),
            sa.Column("service_area", sa.String(length=500)),
            sa.Column("notes", sa.Text()),
            sa.Column("source_import_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("import_jobs.id")),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )

    if not table_exists("emergency_services"):
        op.create_table(
            "emergency_services",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("service_type", sa.String(length=50), nullable=False, server_default="fire"),
            sa.Column("name", sa.String(length=500), nullable=False),
            sa.Column("address", sa.String(length=500)),
            sa.Column("phone", sa.String(length=100)),
            sa.Column("dispatcher_phone", sa.String(length=100)),
            sa.Column("municipality", sa.String(length=200)),
            sa.Column("settlement", sa.String(length=200)),
            sa.Column("latitude", sa.String(length=50)),
            sa.Column("longitude", sa.String(length=50)),
            sa.Column("service_area", sa.String(length=500)),
            sa.Column("notes", sa.Text()),
            sa.Column("source_import_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("import_jobs.id")),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )

    if not table_exists("pmla_questionnaires"):
        op.create_table(
            "pmla_questionnaires",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
            sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hazardous_facilities.id")),
            sa.Column("title", sa.String(length=500)),
            sa.Column("data", jsonb, server_default="{}"),
            sa.Column("source_import_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("import_jobs.id")),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )


def downgrade() -> None:
    for table in [
        "pmla_questionnaires",
        "emergency_services",
        "emergency_rescue_units",
        "import_rows",
        "import_jobs",
    ]:
        if table_exists(table):
            op.drop_table(table)
