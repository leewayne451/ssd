"""Add quantity to CartItem

Revision ID: d5f8e2a1c3b9
Revises: b2a1c4d7e9f0
Create Date: 2026-07-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5f8e2a1c3b9'
down_revision = 'c3d2e1f00001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.drop_column('quantity')
