# builtins
import os
from dotenv import load_dotenv
from unittest import TestCase

# sqlalchemy
from alembic.util import CommandError
from sqlalchemy import text

# local
from browseterm_db.common.config import DBConfig, TEST_MIGRATIONS_DIR
from browseterm_db.migrations.migrator import Migrator

# load the environment variables
load_dotenv('.env')


class TestMigrations(TestCase):
    '''
    Test the migrations.
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.migrator: Migrator = Migrator(self.db_config, TEST_MIGRATIONS_DIR, versions_subdir="test_versions")
        self.migrator.reset_database()  # reset the database
        # delete all files in the versions directory
        self.migrator.reset_migrations()

    def test_a_successful_connection(self) -> None:
        """Ensure DBConfig connects successfully to the database."""
        try:
            with self.db_config.engine.connect() as conn:
                result = conn.execute(text("SELECT current_database();"))
                value = result.fetchone()
                self.assertEqual(value[0], "browseterm_test")
        except Exception as e:
            self.fail(f"Database connection failed: {e}")

    def test_b_mock_unsuccessful_connection(self) -> None:
        """Ensure DBConfig fails to connect to the database."""
        fail_db_config: DBConfig = DBConfig(
            username="namah",
            password="test123",
            host="localhost",
            port=5432,
            database="nonexistent_database"
        )
        try:
            with fail_db_config.engine.connect() as conn:
                result = conn.execute(text("SELECT current_database();"))
                value = result.fetchone()
                self.assertEqual(value[0], "nonexistent_database")
        except Exception as e:
            self.assertEqual('database "nonexistent_database" does not exist\n' in str(e), True)

    def test_c_migrations(self) -> None:
        '''
        1. If there are no migrations, it should create a new one and return the revision id.
        2. If there are migrations, it should create a new one and return the revision id.
            - If there are no changes, it should return the same revision id.
        '''
        revision_id: str = self.migrator.revision('Initial migration - create all tables', autogenerate=True)
        # test if the files are created
        versions_dir: str = os.path.join(TEST_MIGRATIONS_DIR, "test_versions")
        self.assertEqual(os.path.exists(versions_dir), True)
        self.assertEqual(f'{revision_id}_initial_migration_create_all_tables.py' in os.listdir(versions_dir), True)

        # this will fail because the database is not up to date
        try:
            self.migrator.revision('DUPLICATE Initial migration - create all tables', autogenerate=True)
        except CommandError as e:
            self.assertEqual('Target database is not up to date' in str(e), True)

        # Apply the migration to bring database up to date
        self.migrator.upgrade()
        # test if we can get all the tables;
        tables: list = self.migrator.get_tables()
        required_tables = ['alembic_version', 'containers', 'orders', 'subscriptions', 'subscription_types', 'users']
        self.assertEqual(set(tables) - set(required_tables), set())

        '''
        - Now if you call revision again with no model changes:
            - It should create a new migration and return the new revision id.
            - But since nothing changeed in the models, the migration file will have nothing in it upgrade and downgrade methods.
        '''

        new_revision_id: str = self.migrator.revision('DUPLICATE Initial migration - create all tables', autogenerate=True)
        self.assertNotEqual(
            new_revision_id,
            revision_id,
            "Should return different revision when no model changes. Migration file will have nothing in it upgrade and downgrade methods."
        )

        # try hitting upgrade again. Nothing should change.
        self.migrator.upgrade()
        # test if we can get all the tables;
        tables: list = self.migrator.get_tables()
        required_tables = ['alembic_version', 'containers', 'orders', 'subscriptions', 'subscription_types', 'users']
        self.assertEqual(set(tables) - set(required_tables), set())

        '''
        NOTE:
        - Our setUp method resets the database and migrations for each test.
        - So if we want to create another test case we need to setup everything again.
        - To avoid that we put all migration related tests in test_c_migrations.
        '''
        # reset the database, this will delete all the tables from the database but not the migration files.
        self.migrator.reset_database()
        self.migrator.upgrade()  # hit upgrade again, all tables should come back again.
        tables: list = self.migrator.get_tables()
        required_tables = ['alembic_version', 'containers', 'orders', 'subscriptions', 'subscription_types', 'users']
        self.assertEqual(set(tables) - set(required_tables), set())


class ZZZCleanup(TestCase):
    '''
    Cleanup the database after the tests.
    '''
    def test_cleanup(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.migrator: Migrator = Migrator(self.db_config, TEST_MIGRATIONS_DIR, versions_subdir="test_versions")
        self.migrator.reset_database()
        # delete all files in the versions directory
        self.migrator.reset_migrations()
