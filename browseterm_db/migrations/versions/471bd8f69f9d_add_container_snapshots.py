"""add container_snapshots table and containers.next_snapshot_sequence

P15 (see ~/browseterm/p.md's "P15" section, plan section 5.4/5.5).

Revision ID: 471bd8f69f9d
Revises: f2a3b4c5d6e7
Create Date: 2026-08-31

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '471bd8f69f9d'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'containers',
        sa.Column('next_snapshot_sequence', sa.Integer(), nullable=False, server_default='1'),
    )
    op.create_table(
        'container_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('container_id', sa.UUID(), nullable=False),
        sa.Column('version_sequence', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('image_repository', sa.String(length=500), nullable=False),
        sa.Column('image_reference', sa.String(length=500), nullable=True),
        sa.Column('registry_digest', sa.String(length=255), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', name='snapshotstatus'), nullable=False),
        sa.Column('error_detail', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['container_id'], ['containers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('container_id', 'request_id', name='uq_container_snapshot_container_request'),
        sa.UniqueConstraint('container_id', 'version_sequence', name='uq_container_snapshot_container_version'),
    )
    op.create_index('idx_container_snapshot_container_id', 'container_snapshots', ['container_id'], unique=False)
    op.create_index('idx_container_snapshot_status', 'container_snapshots', ['status'], unique=False)
    op.create_index('idx_container_snapshot_created_at', 'container_snapshots', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_container_snapshot_created_at', table_name='container_snapshots')
    op.drop_index('idx_container_snapshot_status', table_name='container_snapshots')
    op.drop_index('idx_container_snapshot_container_id', table_name='container_snapshots')
    op.drop_table('container_snapshots')
    sa.Enum(name='snapshotstatus').drop(op.get_bind(), checkfirst=True)
    op.drop_column('containers', 'next_snapshot_sequence')
