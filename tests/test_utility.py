"""
Test utility functionality
"""

# builtins
import os
import json
from unittest import TestCase

# third party
from dotenv import load_dotenv

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from db_state_manager.state_manager import DBStateManager


load_dotenv('.env')


class TestUtility(TestCase):
    '''
    Test the utility functionality
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.utility = DBStateManager(self.db_config)

    def test_1_load_json_files(self) -> None:
        '''
        Test loading JSON files
        '''
        print('test_1_load_json_files: ', end="")
        
        # Test loading subscription types
        sub_data = self.utility.load_json_file("subscription_types.json")
        self.assertIsInstance(sub_data, list)
        self.assertGreater(len(sub_data), 0)
        
        # Test loading images
        img_data = self.utility.load_json_file("images.json")
        self.assertIsInstance(img_data, list)
        self.assertGreater(len(img_data), 0)
        
        print('OK')

    def test_2_sync_images(self) -> None:
        '''
        Test syncing images from JSON
        '''
        print('test_2_sync_images: ', end="")
        
        # Sync images
        result = self.utility.sync_images("images.json")
        self.assertTrue(result.success)
        
        # Check status
        status_result = self.utility.get_images_status()
        self.assertTrue(status_result.success)
        self.assertGreater(status_result.data["total"], 0)
        
        print('OK')

    def test_3_sync_subscription_types(self) -> None:
        '''
        Test syncing subscription types from JSON
        '''
        print('test_3_sync_subscription_types: ', end="")
        
        # Sync subscription types
        result = self.utility.sync_subscription_types("subscription_types.json")
        self.assertTrue(result.success)
        
        # Check status
        status_result = self.utility.get_subscription_types_status()
        self.assertTrue(status_result.success)
        self.assertGreater(status_result.data["total"], 0)
        
        print('OK')

    def test_4_sync_all(self) -> None:
        '''
        Test syncing all data
        '''
        print('test_4_sync_all: ', end="")
        
        # Sync all
        result = self.utility.sync_all()
        self.assertTrue(result.success)
        
        # Check both statuses
        sub_status = self.utility.get_subscription_types_status()
        img_status = self.utility.get_images_status()
        
        self.assertTrue(sub_status.success)
        self.assertTrue(img_status.success)
        
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
