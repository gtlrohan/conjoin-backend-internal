"""add_is_positive_to_card_completion

Revision ID: 882a637ec342
Revises: 4957533a9ab9
Create Date: 2025-09-29 17:45:36.937509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '882a637ec342'
down_revision: Union[str, None] = '4957533a9ab9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_positive column to CardCompletionDetail table
    op.add_column('CardCompletionDetail', sa.Column('is_positive', sa.Boolean(), nullable=True))


def downgrade() -> None:
    # Remove is_positive column from CardCompletionDetail table
    op.drop_column('CardCompletionDetail', 'is_positive')
