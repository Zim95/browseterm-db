"""add device_command_created notify trigger (migration Part 6)

Revision ID: b7e2f4a9c1d3
Revises: a3f7c9d2e1b4
Create Date: 2026-09-21 14:00:00.000000

Fires once per newly-inserted device_commands row so the Cloud Device Control gRPC server can
push ExecuteCommand to an already-connected device immediately, instead of relying only on the
next poll/reconnect. Mirrors a1b2c3d4e5f6_add_container_status_notify_trigger.py's pattern.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'b7e2f4a9c1d3'
down_revision = 'a3f7c9d2e1b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_device_command_created()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'device_command_created',
                json_build_object(
                    'id', NEW.id,
                    'device_id', NEW.device_id,
                    'user_id', NEW.user_id,
                    'container_id', NEW.container_id,
                    'operation', NEW.operation,
                    'created_at', NEW.created_at
                )::text
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER device_command_created_trigger
        AFTER INSERT ON device_commands
        FOR EACH ROW
        EXECUTE FUNCTION notify_device_command_created();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS device_command_created_trigger ON device_commands")
    op.execute("DROP FUNCTION IF EXISTS notify_device_command_created()")
