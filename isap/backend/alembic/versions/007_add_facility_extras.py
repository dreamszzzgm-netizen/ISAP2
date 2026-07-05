"""add facility extras: coordinates, type, dates

Revision ID: 007
Revises: 006
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def column_exists(table, column):
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return result.scalar()


def upgrade() -> None:
    if not column_exists("hazardous_facilities", "latitude"):
        op.add_column("hazardous_facilities", sa.Column("latitude", sa.Numeric(10, 7)))
    if not column_exists("hazardous_facilities", "longitude"):
        op.add_column("hazardous_facilities", sa.Column("longitude", sa.Numeric(10, 7)))
    if not column_exists("hazardous_facilities", "commissioning_date"):
        op.add_column("hazardous_facilities", sa.Column("commissioning_date", sa.Date()))
    if not column_exists("hazardous_facilities", "inventory_number"):
        op.add_column("hazardous_facilities", sa.Column("inventory_number", sa.String(100)))

    bind = op.get_bind()
    idx_exists = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname='idx_hf_coords')"
    )).scalar()
    if not idx_exists:
        op.create_index("idx_hf_coords", "hazardous_facilities", ["latitude", "longitude"])


def downgrade() -> None:
    bind = op.get_bind()
    idx_exists = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname='idx_hf_coords')"
    )).scalar()
    if idx_exists:
        op.drop_index("idx_hf_coords")
    if column_exists("hazardous_facilities", "inventory_number"):
        op.drop_column("hazardous_facilities", "inventory_number")
    if column_exists("hazardous_facilities", "commissioning_date"):
        op.drop_column("hazardous_facilities", "commissioning_date")
    if column_exists("hazardous_facilities", "longitude"):
        op.drop_column("hazardous_facilities", "longitude")
    if column_exists("hazardous_facilities", "latitude"):
        op.drop_column("hazardous_facilities", "latitude")
