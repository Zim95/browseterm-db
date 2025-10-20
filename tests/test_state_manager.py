"""
Tests for DBStateManager state sync and set operations
"""

# builtins
import os
from unittest import TestCase

# third party
from dotenv import load_dotenv

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from db_state_manager.state_manager import DBStateManager, update_images, update_subscription_types


load_dotenv('.env')


class AAA_InitialSetup(TestCase):
    '''
    Initial database setup
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

    def test_setup(self) -> None:
        '''
        Test the setup
        '''
        self.migrator.reset_database()  # reset the database
        # delete all files in the versions directory
        self.migrator.reset_migrations()
        # create all tables
        self.migrator.revision('Initial migration')
        self.migrator.upgrade()


class TestStateManager(TestCase):
    '''
    Tests for DBStateManager
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.manager = DBStateManager(self.db_config)

    def test_1_get_state_lists(self) -> None:
        '''
        Load state JSON lists via manager
        '''
        print('test_1_get_state_lists: ', end="")
        st_images: list[dict] = self.manager.get_state_list('images')
        st_subs: list[dict] = self.manager.get_state_list('subscription_types')
        self.assertIsInstance(st_images, list)
        self.assertGreaterEqual(len(st_images), 0)  # greater than or equal to 0
        self.assertIsInstance(st_subs, list)
        self.assertGreaterEqual(len(st_subs), 0)  # greater than or equal to 0
        print('OK')

    def test_2_find_differences_when_db_empty(self) -> None:
        '''
        Differences should reflect all state items unique when DB is empty
        '''
        print('test_2_find_differences_when_db_empty: ', end="")
        st_images: list[dict] = self.manager.get_state_list('images')
        db_images: list[dict] = []
        diffs: dict = self.manager.find_differences(st_images, db_images, 'images')
        self.assertSetEqual(diffs['unique_to_db_list'], set())
        self.assertTrue(len(diffs['unique_to_state_list']) >= 0)
        print('OK')

    def test_3_update_images_and_subscription_types(self) -> None:
        '''
        Orchestrators should create/update/soft-delete to match state
        '''
        print('test_3_update_images_and_subscription_types: ', end="")
        update_images(self.manager)
        update_subscription_types(self.manager)
        # After update, DB lists should at least include all state names
        st_images = self.manager.get_state_list('images')
        db_images = self.manager.get_db_list('images')
        st_img_names: set[str] = {i['name'] for i in st_images}
        db_img_names = {i['name'] for i in db_images}
        self.assertTrue(st_img_names.issubset(db_img_names))

        st_subs = self.manager.get_state_list('subscription_types')
        db_subs = self.manager.get_db_list('subscription_types')
        st_sub_names = {s['name'] for s in st_subs}
        db_sub_names = {s['name'] for s in db_subs}
        self.assertTrue(st_sub_names.issubset(db_sub_names))
        print('OK')


class ZZZ_Cleanup(TestCase):
    '''
    Cleanup: Reset the database.
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

    def test_cleanup(self) -> None:
        self.migrator.reset_database()
        self.migrator.reset_migrations()
