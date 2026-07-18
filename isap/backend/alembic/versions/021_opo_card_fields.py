"""add ОПО card fields to hazardous_facilities

Adds characterization fields for the ОПО card:
- opo_full_name: полное наименование ОПО
- classification: признаки классификации 4.1–4.12 (JSONB array)
- work_processes: процессы и работы 2.1–2.6 (JSONB dict)
- licensed_activities: лицензируемые виды деятельности (JSONB array)
- composition_structures: здания, сооружения, площадки (JSONB array)
- nearby_hazardous: опасные вещества на других ОПО ближе 500м (JSONB array)

All new fields are nullable — existing data is unaffected.
No changes to PMMLA pipeline, mapper, schema, template, or renderer.

Revision: 021
Revises: 020
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hazardous_facilities",
        sa.Column("opo_full_name", sa.String(500), nullable=True),
    )
    op.add_column(
        "hazardous_facilities",
        sa.Column("classification", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "hazardous_facilities",
        sa.Column("work_processes", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "hazardous_facilities",
        sa.Column("licensed_activities", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "hazardous_facilities",
        sa.Column("composition_structures", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "hazardous_facilities",
        sa.Column("nearby_hazardous", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hazardous_facilities", "nearby_hazardous")
    op.drop_column("hazardous_facilities", "composition_structures")
    op.drop_column("hazardous_facilities", "licensed_activities")
    op.drop_column("hazardous_facilities", "work_processes")
    op.drop_column("hazardous_facilities", "classification")
    op.drop_column("hazardous_facilities", "opo_full_name")
