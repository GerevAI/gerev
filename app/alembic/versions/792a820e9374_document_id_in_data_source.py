"""document id_in_data_source

Revision ID: 792a820e9374
Revises: 9c2f5b290b16
Create Date: 2023-03-26 11:27:05.341609

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '792a820e9374'
down_revision = '9c2f5b290b16'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.add_column('document', sa.Column('id_in_data_source', sa.String(length=64), default='__none__'))
    except:
        pass


def downgrade() -> None:
    op.drop_column('document', 'id_in_data_source')
