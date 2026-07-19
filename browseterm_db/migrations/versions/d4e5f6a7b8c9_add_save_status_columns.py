"""add save status columns to containers

Revision ID: d4e5f6a7b8c9
Revises: 0f7f0ca831a6
Create Date: 2026-07-19

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = '0f7f0ca831a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Save/snapshot flow state (save_status stored as a string; values from SaveStatus enum)
    op.add_column('containers', sa.Column('save_status', sa.String(length=20), nullable=False, server_default='None'))
    op.add_column('containers', sa.Column('save_error', sa.String(length=1000), nullable=True))
    op.add_column('containers', sa.Column('last_saved_at', sa.DateTime(), nullable=True))

    # Widen saved_image: String(20) is too small for real image names (e.g. "zim95/<pod>-image:latest")
    op.alter_column(
        'containers', 'saved_image',
        existing_type=sa.String(length=20),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'containers', 'saved_image',
        existing_type=sa.String(length=255),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.drop_column('containers', 'last_saved_at')
    op.drop_column('containers', 'save_error')
    op.drop_column('containers', 'save_status')
