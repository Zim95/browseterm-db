"""add devices table

Revision ID: e1f2a3b4c5d6
Revises: d3e4f5a6b7c8
Create Date: 2026-08-30

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'devices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('device_name', sa.String(length=255), nullable=False),
        sa.Column('os', sa.String(length=50), nullable=False),
        sa.Column('architecture', sa.String(length=20), nullable=False),
        sa.Column('runtime_version', sa.String(length=50), nullable=True),
        sa.Column('total_cpu', sa.Integer(), nullable=False),
        sa.Column('total_memory_bytes', sa.BigInteger(), nullable=False),
        sa.Column('total_storage_bytes', sa.BigInteger(), nullable=False),
        sa.Column('allocated_cpu', sa.Integer(), nullable=False),
        sa.Column('allocated_memory_bytes', sa.BigInteger(), nullable=False),
        sa.Column('allocated_storage_bytes', sa.BigInteger(), nullable=False),
        sa.Column('used_cpu', sa.Integer(), nullable=False),
        sa.Column('used_memory_bytes', sa.BigInteger(), nullable=False),
        sa.Column('used_storage_bytes', sa.BigInteger(), nullable=False),
        sa.Column('gpu_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'REVOKED', name='devicestatus'), nullable=False),
        sa.Column('registered_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'device_name', name='uq_device_user_device_name'),
    )
    op.create_index('idx_device_user_id', 'devices', ['user_id'], unique=False)
    op.create_index('idx_device_last_seen_at', 'devices', ['last_seen_at'], unique=False)
    op.create_index('idx_device_status', 'devices', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_device_status', table_name='devices')
    op.drop_index('idx_device_last_seen_at', table_name='devices')
    op.drop_index('idx_device_user_id', table_name='devices')
    op.drop_table('devices')
    sa.Enum(name='devicestatus').drop(op.get_bind(), checkfirst=True)
