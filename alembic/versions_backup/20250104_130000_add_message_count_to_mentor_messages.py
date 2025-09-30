"""Add message_count to mentor_messages table

Revision ID: add_message_count_001
Revises: mentor_messages_001
Create Date: 2025-01-04 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_message_count_001'
down_revision = 'mentor_messages_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add message_count column to mentor_messages table
    op.add_column('mentor_messages', sa.Column('message_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove message_count column from mentor_messages table
    op.drop_column('mentor_messages', 'message_count') 