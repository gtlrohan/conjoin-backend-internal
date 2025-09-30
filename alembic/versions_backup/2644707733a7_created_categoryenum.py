"""Created CategoryEnum

Revision ID: 2644707733a7
Revises: d7aedaa97b56
Create Date: 2024-10-01 14:47:04.449875

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2644707733a7'
down_revision: Union[str, None] = 'd7aedaa97b56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new column with the enum type
    op.add_column('CardDetail', sa.Column('category', sa.Enum('NUTRITION', 'INNER_GOALS', 'RELATIONSHIPS', 'HOBBIES', 'SLEEP', 'EXERCISE', 'SELF_DEVELOPMENT', 'MOOD', name='categoryenum'), nullable=True))

def downgrade() -> None:
    # Drop the new column
    op.drop_column('CardDetail', 'category')
