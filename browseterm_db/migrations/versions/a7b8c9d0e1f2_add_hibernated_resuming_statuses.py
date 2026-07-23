"""add HIBERNATED and RESUMING to the containerstatus enum

The model (ContainerStatus) has had HIBERNATED/RESUMING, but no chain migration ever added them
to the Postgres enum type — so a DB built by replaying the chain lacked them and the reaper's
UPDATE status='HIBERNATED' would fail. This brings the chain in line with the model.

Hand-written because Alembic autogenerate cannot emit enum-value additions (same reason the
existing enum migration 089fb8e7c9e2 is hand-written). Uses ADD VALUE IF NOT EXISTS so it's an
idempotent no-op on databases where the values were already applied.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-23

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PG 12+ allows ADD VALUE inside a transaction (the new value just can't be USED in the same
    # transaction, which we don't). SQLAlchemy stores the enum by NAME, so we add the names.
    op.execute("ALTER TYPE containerstatus ADD VALUE IF NOT EXISTS 'HIBERNATED'")
    op.execute("ALTER TYPE containerstatus ADD VALUE IF NOT EXISTS 'RESUMING'")


def downgrade() -> None:
    # Postgres can't drop a value from an enum, so recreate the type without the two values
    # (mirrors the 089fb8e7c9e2 pattern). Rows in a removed state are mapped to PENDING.
    op.execute("ALTER TYPE containerstatus RENAME TO containerstatus_old")
    op.execute(
        "CREATE TYPE containerstatus AS ENUM "
        "('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN')"
    )
    op.execute("""
        ALTER TABLE containers
        ALTER COLUMN status TYPE containerstatus
        USING CASE
            WHEN status::text IN ('HIBERNATED', 'RESUMING') THEN 'PENDING'
            ELSE status::text
        END::containerstatus
    """)
    op.execute("DROP TYPE containerstatus_old")
