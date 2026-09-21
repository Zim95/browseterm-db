"""add device_commands, device_credentials, and placement/quota columns (migration Part 1)

Revision ID: a3f7c9d2e1b4
Revises: f90a264c4545
Create Date: 2026-09-21 13:00:00.000000

BROWSETERM_CLOUD_CONTROL_PLANE_MIGRATION.md Part 1 - shared state model and database migrations:
  - users.active_device_id: single atomic pointer for the one-active-device invariant.
  - devices: agent_version, startup_id, connection_generation, reserved_cpu/memory/storage.
  - containers: placement_generation, and additive ContainerStatus values (Queued/Creating/
    Hibernating/Deleting/DeviceOffline/Stranded) - every pre-existing value is untouched.
  - device_commands: the new durable command table, with a partial unique index enforcing at
    most one active (Queued/Delivered/Accepted/Running) lifecycle command per container.
  - device_credentials: durable, revocable device credential audit trail (schema only in this
    part - actual token issuance/validation still goes through Redis today; wiring it through to
    this table is Part 4 work, not this migration).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a3f7c9d2e1b4'
down_revision = 'f90a264c4545'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- users.active_device_id --------------------------------------------------------------
    op.add_column('users', sa.Column('active_device_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_users_active_device_id', 'users', 'devices', ['active_device_id'], ['id'], ondelete='SET NULL',
    )

    # ---- devices: new columns ------------------------------------------------------------------
    op.add_column('devices', sa.Column('agent_version', sa.String(length=50), nullable=True))
    op.add_column('devices', sa.Column('startup_id', sa.String(length=100), nullable=True))
    op.add_column('devices', sa.Column('connection_generation', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('devices', sa.Column('reserved_cpu', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('devices', sa.Column('reserved_memory_bytes', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('devices', sa.Column('reserved_storage_bytes', sa.BigInteger(), nullable=False, server_default='0'))

    # ---- containers: placement_generation + additive ContainerStatus values --------------------
    # NOTE: this repo's convention (see a7b8c9d0e1f2/089fb8e7c9e2) is that the Postgres enum type
    # stores the Python Enum MEMBER NAME (e.g. 'HIBERNATED'), not its .value string ('Hibernated')
    # - sa.Enum(ContainerStatus) without values_callable persists .name. Match that here.
    op.add_column('containers', sa.Column('placement_generation', sa.Integer(), nullable=False, server_default='0'))
    for new_value in ('QUEUED', 'CREATING', 'HIBERNATING', 'DELETING', 'DEVICE_OFFLINE', 'STRANDED'):
        op.execute(f"ALTER TYPE containerstatus ADD VALUE IF NOT EXISTS '{new_value}'")

    # ---- device_commands ------------------------------------------------------------------------
    # Unlike f90a264c4545's tunnel_status_enum (an ALTER TABLE ADD COLUMN on an EXISTING table,
    # which does NOT auto-create its enum type), this is a fresh CREATE TABLE - op.create_table
    # below creates commandoperation/commandstatus automatically as part of creating the table, so
    # no separate .create() call is needed (and calling one first would double-create the type).
    command_operation_enum = postgresql.ENUM(
        'CREATE', 'DELETE', 'HIBERNATE', 'RESUME', 'RECONCILE', name='commandoperation',
    )
    command_status_enum = postgresql.ENUM(
        'QUEUED', 'DELIVERED', 'ACCEPTED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', name='commandstatus',
    )

    op.create_table(
        'device_commands',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('container_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('containers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('operation', command_operation_enum, nullable=False),
        sa.Column('placement_generation', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expected_container_state', sa.String(length=20), nullable=True),
        sa.Column('status', command_status_enum, nullable=False, server_default='QUEUED'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('available_at', sa.DateTime(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('progress_stage', sa.String(length=50), nullable=True),
        sa.Column('progress_message', sa.String(length=500), nullable=True),
        sa.Column('result', postgresql.JSON(), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('quota_reserved_cpu', sa.Integer(), nullable=True),
        sa.Column('quota_reserved_memory_bytes', sa.Integer(), nullable=True),
        sa.Column('quota_reserved_storage_bytes', sa.Integer(), nullable=True),
        sa.Column('quota_released_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_device_command_device_status_available', 'device_commands', ['device_id', 'status', 'available_at'])
    op.create_index('idx_device_command_container_id', 'device_commands', ['container_id'])
    op.create_index('idx_device_command_status_updated_at', 'device_commands', ['status', 'updated_at'])
    op.create_index('idx_device_command_user_id', 'device_commands', ['user_id'])
    # Prevent more than one active lifecycle command per container (Part 1 required invariant).
    op.execute(
        "CREATE UNIQUE INDEX uq_device_commands_one_active_per_container ON device_commands (container_id) "
        "WHERE container_id IS NOT NULL AND status IN ('QUEUED', 'DELIVERED', 'ACCEPTED', 'RUNNING')"
    )

    # ---- device_credentials ---------------------------------------------------------------------
    op.create_table(
        'device_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_prefix', sa.String(length=32), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('rotated_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_device_credential_device_id', 'device_credentials', ['device_id'])
    op.create_index('idx_device_credential_token_prefix', 'device_credentials', ['token_prefix'])
    op.create_index('idx_device_credential_revoked_at', 'device_credentials', ['revoked_at'])


def downgrade() -> None:
    op.drop_index('idx_device_credential_revoked_at', table_name='device_credentials')
    op.drop_index('idx_device_credential_token_prefix', table_name='device_credentials')
    op.drop_index('idx_device_credential_device_id', table_name='device_credentials')
    op.drop_table('device_credentials')

    op.execute('DROP INDEX IF EXISTS uq_device_commands_one_active_per_container')
    op.drop_index('idx_device_command_user_id', table_name='device_commands')
    op.drop_index('idx_device_command_status_updated_at', table_name='device_commands')
    op.drop_index('idx_device_command_container_id', table_name='device_commands')
    op.drop_index('idx_device_command_device_status_available', table_name='device_commands')
    op.drop_table('device_commands')
    sa.Enum(name='commandstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='commandoperation').drop(op.get_bind(), checkfirst=True)

    # NOTE: Postgres cannot remove a value from an existing enum type (no ALTER TYPE ... DROP
    # VALUE) - the additive ContainerStatus values from upgrade() are intentionally left in place
    # on downgrade. This mirrors 089fb8e7c9e2_changed_containerstatusenum.py's own precedent in
    # this repo for the same limitation.
    op.drop_column('containers', 'placement_generation')

    op.drop_column('devices', 'reserved_storage_bytes')
    op.drop_column('devices', 'reserved_memory_bytes')
    op.drop_column('devices', 'reserved_cpu')
    op.drop_column('devices', 'connection_generation')
    op.drop_column('devices', 'startup_id')
    op.drop_column('devices', 'agent_version')

    op.drop_constraint('fk_users_active_device_id', 'users', type_='foreignkey')
    op.drop_column('users', 'active_device_id')
