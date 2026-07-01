"""Add admin TOTP 2FA fields to users

Revision ID: b2a1c4d7e9f0
Revises: 1d34f6095820
Create Date: 2026-06-30 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2a1c4d7e9f0'
down_revision = '1d34f6095820'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('totp_secret', sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                'totp_enabled',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('totp_enabled')
        batch_op.drop_column('totp_secret')
