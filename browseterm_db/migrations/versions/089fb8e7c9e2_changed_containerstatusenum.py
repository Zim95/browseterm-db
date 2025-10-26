"""changed ContainerStatusEnum

Revision ID: 089fb8e7c9e2
Revises: 093e4526fa42
Create Date: 2025-10-26 01:06:17.464991

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '089fb8e7c9e2'
down_revision = '093e4526fa42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Recreate the enum with all new values
    op.execute("ALTER TYPE containerstatus RENAME TO containerstatus_old")
    op.execute("CREATE TYPE containerstatus AS ENUM ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN')")
    
    # Step 2: Alter the column to use the new enum, converting old values
    op.execute("""
        ALTER TABLE containers 
        ALTER COLUMN status TYPE containerstatus 
        USING CASE
            WHEN status::text = 'STOPPED' THEN 'PENDING'
            WHEN status::text = 'DELETED' THEN 'UNKNOWN'
            WHEN status::text = 'RUNNING' THEN 'RUNNING'
            WHEN status::text = 'FAILED' THEN 'FAILED'
            ELSE 'PENDING'
        END::containerstatus
    """)
    
    # Step 3: Drop old enum
    op.execute("DROP TYPE containerstatus_old")


def downgrade() -> None:
    # Update existing records back to old statuses
    op.execute("""
        UPDATE containers 
        SET status = 'STOPPED' 
        WHERE status = 'PENDING'
    """)
    op.execute("""
        UPDATE containers 
        SET status = 'DELETED' 
        WHERE status = 'UNKNOWN'
    """)
    
    # Revert enum type back to old values
    op.execute("ALTER TYPE containerstatus RENAME TO containerstatus_new")
    op.execute("CREATE TYPE containerstatus AS ENUM ('RUNNING', 'STOPPED', 'FAILED', 'DELETED')")
    op.execute("""
        ALTER TABLE containers 
        ALTER COLUMN status TYPE containerstatus 
        USING status::text::containerstatus
    """)
    op.execute("DROP TYPE containerstatus_new")
