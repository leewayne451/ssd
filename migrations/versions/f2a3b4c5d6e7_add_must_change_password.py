"""add users.must_change_password for forced first-login rotation

Revision ID: f2a3b4c5d6e7
Revises: d1a2b3c4e5f6
Create Date: 2026-07-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a3b4c5d6e7'
down_revision = 'd1a2b3c4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('must_change_password', sa.Boolean(), nullable=False,
                      server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('must_change_password')
