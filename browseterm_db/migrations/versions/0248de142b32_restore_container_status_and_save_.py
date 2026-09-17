"""restore container status and save status notify triggers

A production database bootstrapped via init.py's SetupInitialMigrations (reset_database +
one fresh --autogenerate revision) silently loses every hand-written raw-SQL migration, because
Alembic's autogenerate only diffs SQLAlchemy model metadata (tables/columns/indexes/enums) - it
has no way to see a CREATE FUNCTION/CREATE TRIGGER written via op.execute(), so it never
regenerates one. This is exactly what happened deploying browseterm-server-cloud to production
(puhtaeto-prod-o1): the two NOTIFY triggers originally added by a1b2c3d4e5f6 and e5f6a7b8c9d0
(function body later extended by d3e4f5a6b7c8) never existed on the fresh DB at all, silently
breaking the Postgres LISTEN/NOTIFY -> SSE -> browser live-update pipeline (status updates
happened correctly in the DB, but the frontend never found out).

Idempotent by design (CREATE OR REPLACE FUNCTION, DROP TRIGGER IF EXISTS before CREATE) so it's
safe to apply even against a database where these were already manually restored out-of-band.

Revision ID: 0248de142b32
Revises: 471bd8f69f9d
Create Date: 2026-09-18 01:18:53.271061

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '0248de142b32'
down_revision = '471bd8f69f9d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_container_status_change()
        RETURNS TRIGGER AS $$
        BEGIN
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
    op.execute("DROP TRIGGER IF EXISTS container_status_change_trigger ON containers")
    op.execute("""
        CREATE TRIGGER container_status_change_trigger
        AFTER UPDATE ON containers
        FOR EACH ROW
        EXECUTE FUNCTION notify_container_status_change();
    """)

    # Final cumulative body (d3e4f5a6b7c8's CREATE OR REPLACE over e5f6a7b8c9d0's original),
    # including last_saved_at/last_save_attempted_at in the payload.
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
    op.execute("DROP TRIGGER IF EXISTS container_save_status_change_trigger ON containers")
    op.execute("""
        CREATE TRIGGER container_save_status_change_trigger
        AFTER UPDATE ON containers
        FOR EACH ROW
        EXECUTE FUNCTION notify_container_save_status_change();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS container_status_change_trigger ON containers")
    op.execute("DROP FUNCTION IF EXISTS notify_container_status_change()")
    op.execute("DROP TRIGGER IF EXISTS container_save_status_change_trigger ON containers")
    op.execute("DROP FUNCTION IF EXISTS notify_container_save_status_change()")
