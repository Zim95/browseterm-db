"""add device tunnel state for remote access

Revision ID: f90a264c4545
Revises: 0248de142b32
Create Date: 2026-09-18 14:40:15.324645

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f90a264c4545'
down_revision = '0248de142b32'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Unlike e1f2a3b4c5d6_add_devices_table.py's enum column (part of a fresh CREATE TABLE, where
    # SQLAlchemy emits the CREATE TYPE automatically), add_column against an EXISTING table does
    # not auto-create the enum type - it must be created explicitly first, or the ALTER TABLE
    # fails with 'type "tunnelstatus" does not exist'.
    tunnel_status_enum = sa.Enum('ONLINE', 'OFFLINE', name='tunnelstatus')
    tunnel_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('devices', sa.Column('tunnel_provider', sa.String(length=50), nullable=True))
    op.add_column('devices', sa.Column('tunnel_public_url', sa.String(length=2048), nullable=True))
    op.add_column('devices', sa.Column('tunnel_status', tunnel_status_enum, nullable=True))
    # server_default so this applies cleanly to the existing devices table's real rows -
    # nullable=False with no default would fail against any row already present.
    op.add_column('devices', sa.Column('tunnel_generation', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('devices', sa.Column('tunnel_connected_at', sa.DateTime(), nullable=True))
    op.add_column('devices', sa.Column('tunnel_last_heartbeat_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('devices', 'tunnel_last_heartbeat_at')
    op.drop_column('devices', 'tunnel_connected_at')
    op.drop_column('devices', 'tunnel_generation')
    op.drop_column('devices', 'tunnel_status')
    op.drop_column('devices', 'tunnel_public_url')
    op.drop_column('devices', 'tunnel_provider')
    sa.Enum(name='tunnelstatus').drop(op.get_bind(), checkfirst=True)
