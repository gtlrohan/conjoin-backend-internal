"""Added special action to CardDetail

Revision ID: deee5da3b87e
Revises: e726b5492d87
Create Date: 2024-09-30 15:50:37.156613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Enum


# revision identifiers, used by Alembic.
revision: str = 'deee5da3b87e'
down_revision: Union[str, None] = 'e726b5492d87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # Create the enum type first
    specialactions = Enum('NONE', 'BREATHING', 'AFFIRMATION', name='specialactions')
    specialactions.create(op.get_bind(), checkfirst=True)

    # Now add the column
    op.add_column('CardDetail', sa.Column('special_card_action', sa.Enum('NONE', 'BREATHING', 'AFFIRMATION', name='specialactions'), nullable=True))

def downgrade() -> None:
    # Your existing downgrade logic
    op.drop_column('CardDetail', 'special_card_action')

    # Drop the enum type
    op.execute('DROP TYPE specialactions')