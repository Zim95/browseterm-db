"""add device_id column to containers

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-30

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tracks which device is currently hosting a container's active runtime. NULL once the
    # container is fully hibernated/portable (no active runtime on any device). ON DELETE SET NULL
    # so removing a device only clears the association, never the container/workspace itself.
    op.add_column('containers', sa.Column('device_id', sa.UUID(), nullable=True))
    op.create_index('idx_container_device_id', 'containers', ['device_id'], unique=False)
    op.create_foreign_key(
        'fk_containers_device_id_devices',
        'containers', 'devices',
        ['device_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_containers_device_id_devices', 'containers', type_='foreignkey')
    op.drop_index('idx_container_device_id', table_name='containers')
    op.drop_column('containers', 'device_id')
