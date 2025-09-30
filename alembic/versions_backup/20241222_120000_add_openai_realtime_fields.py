"""Add OpenAI Realtime API fields to voice therapy sessions

Revision ID: openai_realtime_001
Revises: 28eef818ed5f
Create Date: 2024-12-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'openai_realtime_001'
down_revision = '28eef818ed5f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns for OpenAI Realtime API
    op.add_column('voice_therapy_sessions', sa.Column('openai_session_id', sa.String(), nullable=True))
    op.add_column('voice_therapy_sessions', sa.Column('ephemeral_token_expires', sa.DateTime(), nullable=True))
    
    # Update existing records (set openai_session_id to match session_id for backward compatibility)
    op.execute("UPDATE voice_therapy_sessions SET openai_session_id = session_id WHERE openai_session_id IS NULL")
    
    # Make openai_session_id non-nullable after update
    op.alter_column('voice_therapy_sessions', 'openai_session_id', nullable=False)


def downgrade() -> None:
    # Remove the OpenAI Realtime API fields
    op.drop_column('voice_therapy_sessions', 'ephemeral_token_expires')
    op.drop_column('voice_therapy_sessions', 'openai_session_id') 