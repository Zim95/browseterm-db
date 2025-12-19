"""add container status notify trigger

Revision ID: a1b2c3d4e5f6
Revises: 089fb8e7c9e2
Create Date: 2025-12-15

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '089fb8e7c9e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the notify function for container status changes
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_container_status_change()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only notify if status actually changed
            IF OLD.status IS DISTINCT FROM NEW.status THEN
                PERFORM pg_notify(
                    'container_status_change',
                    json_build_object(
                        'id', NEW.id,
                        'user_id', NEW.user_id,
                        'name', NEW.name,
                        'old_status', OLD.status,
                        'new_status', NEW.status,
                        'updated_at', NEW.updated_at
                    )::text
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger on containers table
    op.execute("""
        CREATE TRIGGER container_status_change_trigger
        AFTER UPDATE ON containers
        FOR EACH ROW
        EXECUTE FUNCTION notify_container_status_change();
    """)


def downgrade() -> None:
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS container_status_change_trigger ON containers")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS notify_container_status_change()")
