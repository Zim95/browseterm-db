"""add container save status notify trigger

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-19

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Notify function for container SAVE status changes (separate channel from the pod-status trigger)
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_container_save_status_change()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Only notify if the save_status actually changed
            IF OLD.save_status IS DISTINCT FROM NEW.save_status THEN
                PERFORM pg_notify(
                    'container_save_status_change',
                    json_build_object(
                        'id', NEW.id,
                        'user_id', NEW.user_id,
                        'name', NEW.name,
                        'save_status', NEW.save_status,
                        'saved_image', NEW.saved_image,
                        'save_error', NEW.save_error,
                        'updated_at', NEW.updated_at
                    )::text
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER container_save_status_change_trigger
        AFTER UPDATE ON containers
        FOR EACH ROW
        EXECUTE FUNCTION notify_container_save_status_change();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS container_save_status_change_trigger ON containers")
    op.execute("DROP FUNCTION IF EXISTS notify_container_save_status_change()")
