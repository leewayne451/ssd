"""add cartitem quantity

Revision ID: 2b1f9a0c3e4a
Revises: 1d34f6095820
Create Date: 2026-07-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2b1f9a0c3e4a'
down_revision = 'c3d2e1f00001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cart_items', sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    op.drop_column('cart_items', 'quantity')
