"""widen device_commands quota_reserved_{memory,storage}_bytes to bigint

Both columns store a byte count (a resource limit like memory_limit/storage_limit parsed to
bytes - see device_command_ops.py's callers), the same kind of value devices.allocated_memory_bytes/
used_memory_bytes/allocated_storage_bytes/used_storage_bytes already store as bigint. These two
were left as a plain 32-bit integer (max ~2.1GB) in the original migration that added this table -
a real, production-blocking bug: any container with a memory or storage limit at or above ~2GB
(a routine, unremarkable size) fails to resume with `psycopg2.errors.NumericValueOutOfRange`,
since the INSERT into device_commands can't hold the value at all. `quota_reserved_cpu` is left as
integer - a core count, correctly small - matching devices.allocated_cpu/used_cpu's own type.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-09-23 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('device_commands', 'quota_reserved_memory_bytes', type_=sa.BigInteger())
    op.alter_column('device_commands', 'quota_reserved_storage_bytes', type_=sa.BigInteger())


def downgrade() -> None:
    op.alter_column('device_commands', 'quota_reserved_memory_bytes', type_=sa.Integer())
    op.alter_column('device_commands', 'quota_reserved_storage_bytes', type_=sa.Integer())
