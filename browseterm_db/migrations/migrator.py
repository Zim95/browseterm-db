"""
Migrator class to handle the migrations.
"""

# builtins
import os

# alembic
from alembic import command
from alembic.config import Config

# local
from browseterm_db.common.config import DBConfig, MIGRATIONS_DIR


class Migrator:
    '''
    This class is used to handle the migrations.
    '''
    def __init__(self, db_config: DBConfig, migrations_dir: str = MIGRATIONS_DIR) -> None:
        self.db_config: DBConfig = db_config
        self.alembic_cfg: Config = Config(os.path.join(migrations_dir, "alembic.ini"))
        self.alembic_cfg.set_main_option("script_location", migrations_dir)
        self.alembic_cfg.set_main_option("sqlalchemy.url", self.db_config.get_db_url())
        self.migrations_dir: str = migrations_dir

    def upgrade(self, revision: str = "head") -> None:
        """Apply migrations up to the given revision (default: latest)."""
        command.upgrade(self.alembic_cfg, revision)

    def downgrade(self, revision: str = "-1") -> None:
        """Revert migrations."""
        command.downgrade(self.alembic_cfg, revision)

    def history(self) -> None:
        """Show migration history."""
        command.history(self.alembic_cfg)

    def current(self) -> None:
        """Show current DB revision."""
        command.current(self.alembic_cfg)

    def revision(self, message: str = "auto", autogenerate: bool = True) -> str:
        """Create a new revision file with autogenerate option.
        
        Returns:
            str: The revision ID of the created migration, or existing revision ID if already exists
        """
        import os
        from alembic.script import ScriptDirectory
        
        # Check if migrations already exist
        versions_dir = os.path.join(self.migrations_dir, "versions")
        
        if os.path.exists(versions_dir):
            existing_files = [f for f in os.listdir(versions_dir) if f.endswith('.py')]
            if existing_files:
                print(f"Migration files already exist: {existing_files}")
                # Get the current head revision
                script_dir = ScriptDirectory.from_config(self.alembic_cfg)
                head_revision = script_dir.get_current_head()
                if head_revision:
                    print(f"Current head revision: {head_revision}")
                    print("Checking for new model changes...")
                else:
                    print("Found migration files but no head revision. This might indicate a problem.")

        # Always attempt to create migration - let Alembic's autogenerate decide if there are changes
        print(f"Creating migration: {message}")
        try:
            revision_result = command.revision(self.alembic_cfg, message=message, autogenerate=autogenerate)
            # Get the revision ID from the result
            if hasattr(revision_result, 'revision'):
                revision_id = revision_result.revision
            else:
                # Fallback: get the latest file created
                new_files = [f for f in os.listdir(versions_dir) if f.endswith('.py')]
                if new_files:
                    latest_file = max(new_files, key=lambda x: os.path.getctime(os.path.join(versions_dir, x)))
                    revision_id = latest_file.split('_')[0]  # Extract revision ID from filename
                else:
                    revision_id = "unknown"
            if revision_id and revision_id != "unknown":
                print(f"Created new migration with revision ID: {revision_id}")
            else:
                print("No model changes detected - no new migration created")
            return revision_id
        except Exception as e:
            print(f"Error creating migration: {e}")
            raise
    
    def reset_database(self) -> None:
        """
        Reset the database by dropping all tables and alembic_version.
        Delete the ENUM types from the database.
        """
        from sqlalchemy import text
        print("Resetting database...")
        with self.db_config.engine.connect() as conn:
            # Drop alembic_version table if it exists
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
            # Drop all other tables (in case some exist)
            conn.execute(text("""
                DROP TABLE IF EXISTS orders CASCADE;
                DROP TABLE IF EXISTS containers CASCADE;
                DROP TABLE IF EXISTS subscriptions CASCADE;
                DROP TABLE IF EXISTS subscription_types CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
            """))
            # Drop all custom enum types
            conn.execute(text("""
                DROP TYPE IF EXISTS orderscurrency CASCADE;
                DROP TYPE IF EXISTS subscriptiontypecurrency CASCADE;
                DROP TYPE IF EXISTS authprovider CASCADE;
                DROP TYPE IF EXISTS orderstatus CASCADE;
                DROP TYPE IF EXISTS subscriptionstatus CASCADE;
                DROP TYPE IF EXISTS containerstatus CASCADE;
            """))
            conn.commit()
        print("Database reset complete.")

    def reset_migrations(self) -> None:
        """Reset the migrations by deleting all files in the versions directory."""
        import shutil
        versions_dir: str = os.path.join(self.migrations_dir, "versions")
        if not os.path.exists(versions_dir):
            print("Versions directory doesn't exist, nothing to reset")
            return
        for item in os.listdir(versions_dir):
            item_path = os.path.join(versions_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    print(f"Removed file: {item}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"Removed directory: {item}")
            except Exception as e:
                print(f"Warning: Could not remove {item}: {e}")
        print("Migration files reset complete")

    def is_database_clean(self) -> bool:
        """Check if database is in a clean state (no tables)."""
        from sqlalchemy import text
        
        with self.db_config.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            table_count = result.scalar()
            return table_count == 0

    def is_migrations_clean(self) -> bool:
        """Check if migrations are in a clean state (no files)."""
        versions_dir: str = os.path.join(self.migrations_dir, "versions")
        if not os.path.exists(versions_dir):
            print("Versions directory doesn't exist, nothing to reset")
            return True
        for item in os.listdir(versions_dir):
            item_path = os.path.join(versions_dir, item)
            if os.path.isfile(item_path):
                print(f"Found file: {item}")
                return False
            elif os.path.isdir(item_path):
                print(f"Found directory: {item}")
                return False
        return True

    def get_tables(self) -> list[str]:
        """Get all tables in the database."""
        from sqlalchemy import text
        with self.db_config.engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"))
            return [table[0] for table in result.fetchall()]
