"""
add linked_user_card_id to voice_therapy_sessions

Revision ID: 20250812_000000
Revises: 20250104_130000_add_message_count_to_mentor_messages
Create Date: 2025-08-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250812_000000'
down_revision = '20250104_130000_add_message_count_to_mentor_messages'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'voice_therapy_sessions',
        sa.Column('linked_user_card_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_voice_sessions_usercard',
        'voice_therapy_sessions',
        'UserCard',
        ['linked_user_card_id'],
        ['card_id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_voice_sessions_usercard', 'voice_therapy_sessions', type_='foreignkey')
    op.drop_column('voice_therapy_sessions', 'linked_user_card_id')


