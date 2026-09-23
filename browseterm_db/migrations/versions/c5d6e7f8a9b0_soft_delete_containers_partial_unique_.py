"""containers: soft-delete-aware unique name constraint

Replaces the plain UniqueConstraint('user_id', 'name') with a partial unique index scoped to
`deleted_at IS NULL`. This is what makes DELETE's new immediate-soft-delete behavior possible
(_delete_container_via_device_command in browseterm-server now stamps deleted_at right away,
before Device Agent has actually confirmed the Kubernetes teardown, so the user can immediately
see it gone and create a new container reusing the same name) - without this change, the old
plain constraint would keep blocking that reuse until the async delete fully completed, which is
exactly the "recreate while the old one is still tearing down" scenario the original two-phase
Local design (delete_container_in_db / delete_container_in_k8s) supported and the Cloud Control
Plane migration's single-call redesign silently dropped. Any number of soft-deleted (deleted_at
IS NOT NULL) rows may now share a name; only one live (deleted_at IS NULL) row per (user_id, name)
is ever allowed.

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-09-24 00:45:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'c5d6e7f8a9b0'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('uq_container_user_name', 'containers', type_='unique')
    op.execute(
        'CREATE UNIQUE INDEX uq_container_user_name ON containers (user_id, name) '
        'WHERE deleted_at IS NULL'
    )


def downgrade() -> None:
    op.execute('DROP INDEX uq_container_user_name')
    op.create_unique_constraint('uq_container_user_name', 'containers', ['user_id', 'name'])
