"""Add transcript column to voice therapy sessions

Revision ID: transcript_column_001
Revises: openai_realtime_001
Create Date: 2024-12-22 13:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'transcript_column_001'
down_revision = 'openai_realtime_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add transcript column to store conversation messages as JSON
    op.add_column('voice_therapy_sessions', sa.Column('transcript', postgresql.JSON(), nullable=True))


def downgrade() -> None:
    # Remove the transcript column
    op.drop_column('voice_therapy_sessions', 'transcript')
