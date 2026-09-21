"""add container_config_json to device_commands (migration Parts 8-11)

Revision ID: c4d8a1e6f2b9
Revises: b7e2f4a9c1d3
Create Date: 2026-09-21 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'c4d8a1e6f2b9'
down_revision = 'b7e2f4a9c1d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('device_commands', sa.Column('container_config_json', sa.String(length=4000), nullable=True))


def downgrade() -> None:
    op.drop_column('device_commands', 'container_config_json')
