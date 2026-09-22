"""add image_tag to container_snapshots

Part 19 (registry): snapshots move from one private Docker Hub repository per (user, container)
to a single fixed repository (`zim95/browseterm`), with per-attempt identity/version carried
entirely in the tag instead: `u_<user_id>_c_<container_id>_v_<version>`. `image_repository` stays
(now always the same fixed value, kept as its own column for schema stability/auditability rather
than removed), this adds the tag half alongside it so the durably-stored reference doesn't depend
on re-deriving it from other columns.

Revision ID: a2b3c4d5e6f7
Revises: d8e9f0a1b2c3
Create Date: 2026-09-22 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('container_snapshots', sa.Column('image_tag', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column('container_snapshots', 'image_tag')
