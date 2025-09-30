"""Merge voice therapy migration chains

Revision ID: merge_voice_therapy_001
Revises: voice_therapy_001, transcript_column_001
Create Date: 2024-12-22 14:00:00.000000

"""


# revision identifiers, used by Alembic.
revision = 'merge_voice_therapy_001'
down_revision = ('voice_therapy_001', 'transcript_column_001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration - no changes needed
    pass


def downgrade() -> None:
    # This is a merge migration - no changes needed
    pass
