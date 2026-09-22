"""add SAVE to the commandoperation enum

Adds a standalone SAVE device command operation - snapshots a container without deleting it
(unlike HIBERNATE, which saves then deletes). Wired the same way as every other command: a
durable device_commands row, delivered over the control stream, Device Agent executes it and
reports a result. No new columns/tables needed - reuses containers.save_status/saved_image and
the existing container_snapshots table exactly as HIBERNATE's save step already does.

Revision ID: d8e9f0a1b2c3
Revises: c4d8a1e6f2b9
Create Date: 2026-09-22 10:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'd8e9f0a1b2c3'
down_revision = 'c4d8a1e6f2b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG 12+ allows ADD VALUE inside a transaction (the new value just can't be USED in the same
    # transaction, which we don't). SQLAlchemy stores the enum by NAME - see a3f7c9d2e1b4's own
    # note on this same convention.
    op.execute("ALTER TYPE commandoperation ADD VALUE IF NOT EXISTS 'SAVE'")


def downgrade() -> None:
    # Postgres cannot remove a value from an existing enum type (no ALTER TYPE ... DROP VALUE) -
    # same limitation and precedent as a7b8c9d0e1f2/a3f7c9d2e1b4. Left in place on downgrade.
    pass
