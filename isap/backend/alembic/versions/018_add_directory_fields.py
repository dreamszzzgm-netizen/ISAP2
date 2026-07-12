"""add directory fields for pasf and emergency services

Revision ID: 018
Revises: 017
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return bool(result.scalar())


def upgrade() -> None:
    # --- EmergencyRescueUnitModel (ПАСФ) ---
    if not column_exists("emergency_rescue_units", "is_active"):
        op.add_column(
            "emergency_rescue_units",
            sa.Column("is_active", sa.SmallInteger(), server_default="1"),
        )
    if not column_exists("emergency_rescue_units", "organization_type"):
        op.add_column(
            "emergency_rescue_units",
            sa.Column("organization_type", sa.String(length=100)),
        )
    if not column_exists("emergency_rescue_units", "director_name"):
        op.add_column(
            "emergency_rescue_units",
            sa.Column("director_name", sa.String(length=300)),
        )
    if not column_exists("emergency_rescue_units", "director_position"):
        op.add_column(
            "emergency_rescue_units",
            sa.Column("director_position", sa.String(length=300)),
        )
    if not column_exists("emergency_rescue_units", "region"):
        op.add_column(
            "emergency_rescue_units",
            sa.Column("region", sa.String(length=200)),
        )

    # --- EmergencyServiceModel ---
    if not column_exists("emergency_services", "is_active"):
        op.add_column(
            "emergency_services",
            sa.Column("is_active", sa.SmallInteger(), server_default="1"),
        )
    if not column_exists("emergency_services", "additional_phone"):
        op.add_column(
            "emergency_services",
            sa.Column("additional_phone", sa.String(length=100)),
        )
    if not column_exists("emergency_services", "verified_at"):
        op.add_column(
            "emergency_services",
            sa.Column("verified_at", sa.String(length=50)),
        )
    if not column_exists("emergency_services", "region"):
        op.add_column(
            "emergency_services",
            sa.Column("region", sa.String(length=200)),
        )


def downgrade() -> None:
    # EmergencyRescueUnitModel
    for col in ("is_active", "organization_type", "director_name",
                "director_position", "region"):
        if column_exists("emergency_rescue_units", col):
            op.drop_column("emergency_rescue_units", col)

    # EmergencyServiceModel
    for col in ("is_active", "additional_phone", "verified_at", "region"):
        if column_exists("emergency_services", col):
            op.drop_column("emergency_services", col)
