"""add last_save_attempted_at column to containers

Records when the most recent save was *initiated* (save_status set to Pending), regardless of
whether it ultimately succeeded or failed -- distinct from last_saved_at, which only updates on
success. Lets the UI show "last successful save" and "last attempt" as two separate timestamps,
next to the current save_status. Hand-written add-column (preserves the NOTIFY triggers),
mirroring the other column migrations.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-24

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('containers', sa.Column('last_save_attempted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('containers', 'last_save_attempted_at')
