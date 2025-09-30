"""add_wellness_metrics_table

Revision ID: 4957533a9ab9
Revises: f21888c42baf
Create Date: 2025-09-29 17:42:46.341972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4957533a9ab9'
down_revision: Union[str, None] = 'f21888c42baf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create daily_wellness_metrics table
    op.create_table('daily_wellness_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('energy_level', sa.Float(), nullable=False),
        sa.Column('stress_level', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.CheckConstraint('energy_level >= 0.0 AND energy_level <= 10.0', name='check_energy_level_range'),
        sa.CheckConstraint('stress_level >= 0.0 AND stress_level <= 10.0', name='check_stress_level_range'),
        sa.ForeignKeyConstraint(['user_id'], ['User.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_daily_wellness_metrics_id'), 'daily_wellness_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_daily_wellness_metrics_user_id'), 'daily_wellness_metrics', ['user_id'], unique=False)
    op.create_index(op.f('ix_daily_wellness_metrics_date'), 'daily_wellness_metrics', ['date'], unique=False)
    op.create_unique_constraint('daily_wellness_metrics_user_id_date_key', 'daily_wellness_metrics', ['user_id', 'date'])


def downgrade() -> None:
    op.drop_constraint('daily_wellness_metrics_user_id_date_key', 'daily_wellness_metrics', type_='unique')
    op.drop_index(op.f('ix_daily_wellness_metrics_date'), table_name='daily_wellness_metrics')
    op.drop_index(op.f('ix_daily_wellness_metrics_user_id'), table_name='daily_wellness_metrics')
    op.drop_index(op.f('ix_daily_wellness_metrics_id'), table_name='daily_wellness_metrics')
    op.drop_table('daily_wellness_metrics')
