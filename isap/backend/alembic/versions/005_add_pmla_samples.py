"""add pmla_samples table

Revision ID: 005
Revises: 004
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pmla_samples',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.String(2000)),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.String(50), server_default='docx'),
        sa.Column('facility_type', sa.String(200)),
        sa.Column('hazard_class', sa.String(50)),
        sa.Column('is_active', sa.SmallInteger(), server_default='1'),
        sa.Column('is_verified', sa.SmallInteger(), server_default='0'),
        sa.Column('usage_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )


def downgrade():
    op.drop_table('pmla_samples')
