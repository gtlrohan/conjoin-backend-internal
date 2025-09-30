"""Add daily wellness metrics table

Revision ID: 20250118_000000_add_daily_wellness_metrics
Revises: 20250812_000000_add_linked_user_card_id_to_voice_sessions
Create Date: 2025-01-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250118_000000_add_daily_wellness_metrics'
down_revision = '20250812_000000'
branch_labels = None
depends_on = None


def upgrade():
    # Create daily_wellness_metrics table
    op.create_table('daily_wellness_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('energy_level', sa.Float(), nullable=False),
        sa.Column('stress_level', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.CheckConstraint('energy_level >= 1.0 AND energy_level <= 10.0', name='check_energy_level_range'),
        sa.CheckConstraint('stress_level >= 1.0 AND stress_level <= 10.0', name='check_stress_level_range'),
        sa.ForeignKeyConstraint(['user_id'], ['User.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on id
    op.create_index(op.f('ix_daily_wellness_metrics_id'), 'daily_wellness_metrics', ['id'], unique=False)
    
    # Create index on user_id for faster queries
    op.create_index('ix_daily_wellness_metrics_user_id', 'daily_wellness_metrics', ['user_id'], unique=False)
    
    # Create index on date for faster date range queries
    op.create_index('ix_daily_wellness_metrics_date', 'daily_wellness_metrics', ['date'], unique=False)
    
    # Create unique index on user_id + date to prevent duplicate entries for same day
    op.create_index('ix_daily_wellness_metrics_user_date', 'daily_wellness_metrics', ['user_id', 'date'], unique=True)


def downgrade():
    # Drop indexes
    op.drop_index('ix_daily_wellness_metrics_user_date', table_name='daily_wellness_metrics')
    op.drop_index('ix_daily_wellness_metrics_date', table_name='daily_wellness_metrics')
    op.drop_index('ix_daily_wellness_metrics_user_id', table_name='daily_wellness_metrics')
    op.drop_index(op.f('ix_daily_wellness_metrics_id'), table_name='daily_wellness_metrics')
    
    # Drop table
    op.drop_table('daily_wellness_metrics')
