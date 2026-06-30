"""Add bio and timestamp columns to profiles

Revision ID: c3d2e1f00001
Revises: b2a1c4d7e9f0
Create Date: 2026-06-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d2e1f00001'
down_revision = 'b2a1c4d7e9f0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bio', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                'created_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch_op.add_column(
            sa.Column(
                'updated_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            )
        )


def downgrade():
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('bio')
