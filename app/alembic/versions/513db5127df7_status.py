"""Your migration message here

Revision ID: 513db5127df7
Revises: 792a820e9374
Create Date: 2023-04-07 05:01:02.427956

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '513db5127df7'
down_revision = '792a820e9374'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('document', sa.Column('status', sa.String(length=32), nullable=True))
    except:
        pass


def downgrade() -> None:
    op.drop_column('document', 'status')
