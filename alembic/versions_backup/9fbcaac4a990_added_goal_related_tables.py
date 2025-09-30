"""Added Goal related tables

Revision ID: 9fbcaac4a990
Revises: 39cf9c9aacbd
Create Date: 2024-11-28 15:26:14.005440
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9fbcaac4a990'
down_revision = '39cf9c9aacbd'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create the Goal table
    op.create_table(
        'Goal',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False)
    )

    # Create the UserGoals table
    op.create_table(
        'UserGoals',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('User.user_id'), nullable=False),
        sa.Column('goal_id', sa.Integer, sa.ForeignKey('Goal.id'), nullable=False),
        sa.Column('target', sa.Integer, nullable=True)
    )

    # Create the Goals2Card table
    op.create_table(
        'Goals2Card',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('goal_id', sa.Integer, sa.ForeignKey('Goal.id'), nullable=False),
        sa.Column('card_id', sa.Integer, sa.ForeignKey('CardDetail.id'), nullable=False)
    )

def downgrade() -> None:
    # Drop the tables in reverse order of creation to avoid errors
    op.drop_table('Goals2Card')
    op.drop_table('UserGoals')
    op.drop_table('Goal')