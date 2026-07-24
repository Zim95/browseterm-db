"""add last_request_id column to containers

Records the request_id of the last request that touched a container, so a failed/broken container
can be traced back to the request that caused it (then follow that request_id across all services'
logs). Hand-written add-column (preserves the NOTIFY triggers), mirroring the other column migrations.

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-07-24

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('containers', sa.Column('last_request_id', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('containers', 'last_request_id')
