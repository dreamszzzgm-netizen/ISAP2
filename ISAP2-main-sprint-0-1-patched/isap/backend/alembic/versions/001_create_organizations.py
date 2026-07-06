"""create_organizations

Revision ID: 001
Revises:
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("inn", sa.String(12), nullable=False, unique=True),
        sa.Column("ogrn", sa.String(15)),
        sa.Column("address", sa.Text()),
        sa.Column("phone", sa.String(50)),
        sa.Column("email", sa.String(200)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("organizations")
