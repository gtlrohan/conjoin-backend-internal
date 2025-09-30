"""Add mentor messages table

Revision ID: mentor_messages_001
Revises: merge_voice_therapy_001
Create Date: 2025-01-04 12:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'mentor_messages_001'
down_revision = 'merge_voice_therapy_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create mentor_messages table
    op.create_table('mentor_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['User.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mentor_messages_id'), 'mentor_messages', ['id'], unique=False)


def downgrade() -> None:
    # Drop mentor_messages table
    op.drop_index(op.f('ix_mentor_messages_id'), table_name='mentor_messages')
    op.drop_table('mentor_messages')
