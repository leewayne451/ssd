"""Merge cart item quantity and profile/timestamp migrations

Revision ID: d4e5f6a7b8c9
Revises: 2b1f9a0c3e4a, c3d2e1f00001
Create Date: 2026-07-04 02:45:00.000000
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d2e1f00001'
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge revision to unify Alembic history.
    pass


def downgrade():
    # No schema changes; this merge node is only for revision history.
    pass
