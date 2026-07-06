"""add reported flag + report_reason to product_listings (FR-14)

Revision ID: d1a2b3c4e5f6
Revises: c72002cec246
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1a2b3c4e5f6'
down_revision = 'c72002cec246'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product_listings', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('reported', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column('report_reason', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('product_listings', schema=None) as batch_op:
        batch_op.drop_column('report_reason')
        batch_op.drop_column('reported')
