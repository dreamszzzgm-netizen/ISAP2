"""add scenario_matrix table

Revision ID: 006
Revises: 005
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scenario_matrix',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('facility_type', sa.String(200), nullable=False),
        sa.Column('hazard_class', sa.String(50), nullable=False),
        sa.Column('scenario_code', sa.String(50), nullable=False),
        sa.Column('scenario_name', sa.String(500), nullable=False),
        sa.Column('factor_type', sa.String(200)),
        sa.Column('calculation_method', sa.String(100)),
        sa.Column('probability', sa.String(50), server_default='средняя'),
        sa.Column('is_active', sa.SmallInteger(), server_default='1'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_scenario_matrix_facility_type', 'scenario_matrix', ['facility_type'])
    op.create_index('ix_scenario_matrix_hazard_class', 'scenario_matrix', ['hazard_class'])


def downgrade():
    op.drop_index('ix_scenario_matrix_hazard_class')
    op.drop_index('ix_scenario_matrix_facility_type')
    op.drop_table('scenario_matrix')
