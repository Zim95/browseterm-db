"""include last_saved_at and last_save_attempted_at in the save-status NOTIFY payload

The container_save_status_change_trigger's payload only carried save_status/saved_image/
save_error/updated_at. The frontend's "last saved" / "last attempt" status widget needs both
timestamps delivered live over the same NOTIFY -> SSE pipeline, not just on page load, so this
CREATE OR REPLACE's the existing trigger function to add them. The trigger itself
(container_save_status_change_trigger, added in e5f6a7b8c9d0) is unchanged -- it already fires
on any UPDATE and references this function by name, so redefining the function's body is
sufficient.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-24

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
                        'last_saved_at', NEW.last_saved_at,
                        'last_save_attempted_at', NEW.last_save_attempted_at,
                        'updated_at', NEW.updated_at
                    )::text
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_container_save_status_change()
        RETURNS TRIGGER AS $$
        BEGIN
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
