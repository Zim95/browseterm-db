'''
Here in tests, we want to test the following:
1. Simple create image should work. We verify each field once the image is created.
2. Duplicate image creation should fail (name is unique).
3. find and find_one should work correctly.
4. update and update_many should work correctly.
5. soft_delete should set is_active to False.
6. soft_delete_many should set is_active to False for multiple images.
7. delete and delete_many should hard delete images.
8. insert_many should create multiple images at once.
'''

# builtins
import os
from unittest import TestCase
import uuid

# third party
from dotenv import load_dotenv

# local
from browseterm_db.operations.image_ops import ImageOps
from browseterm_db.operations import OperationResult
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR


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


class TestImageOps(TestCase):
    '''
    All tests for ImageOps
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.image_ops: ImageOps = ImageOps(self.db_config)

    def tearDown(self) -> None:
        """Clean up all images after each test"""
        self.image_ops.delete_many({})

    def test_1_simple_image_creation_with_field_verification(self) -> None:
        '''
        Test case 1: Simple create image should work. We verify each field once the image is created.
        '''
        print('test_1_simple_image_creation_with_field_verification: ', end="")
        # Create an image
        image_data: dict = {
            "name": "python:3.12-slim",
            "image": "docker.io/library/python:3.12-slim",
            "is_active": True
        }
        result: OperationResult = self.image_ops.insert(image_data)

        # Verify the operation was successful
        self.assertTrue(result.success, f"Image creation failed: {result.error}")
        self.assertEqual(result.message, "Image created successfully")

        # Verify the returned data
        created_image: dict = result.data
        self.assertIsNotNone(created_image)
        self.assertEqual(created_image["name"], image_data["name"])
        self.assertEqual(created_image["image"], image_data["image"])
        self.assertEqual(created_image["is_active"], image_data["is_active"])

        # Verify UUID is generated
        self.assertIsNotNone(created_image["id"])
        # Verify it's a valid UUID
        uuid.UUID(created_image["id"])

        # Verify timestamps are set
        self.assertIsNotNone(created_image["created_at"])
        self.assertIsNotNone(created_image["updated_at"])

        # Verify we can find the image
        find_result = self.image_ops.find_one({"name": image_data["name"]})
        self.assertTrue(find_result.success)
        self.assertIsNotNone(find_result.data)
        self.assertEqual(find_result.data["id"], created_image["id"])
        print('OK')

    def test_2_duplicate_image_creation_should_fail(self) -> None:
        '''
        Test case 2: Duplicate image creation should fail because name is unique.
        '''
        print('test_2_duplicate_image_creation_should_fail: ', end="")
        # Create an image
        image_data: dict = {
            "name": "ubuntu:22.04",
            "image": "docker.io/library/ubuntu:22.04",
            "is_active": True
        }
        result: OperationResult = self.image_ops.insert(image_data)
        self.assertTrue(result.success)

        # Try to create the same image again
        duplicate_result: OperationResult = self.image_ops.insert(image_data)
        self.assertFalse(duplicate_result.success)
        print('OK')

    def test_3_find_and_find_one_operations(self) -> None:
        '''
        Test case 3: find and find_one should work correctly.
        '''
        print('test_3_find_and_find_one_operations: ', end="")
        # Create multiple images
        images_data: list = [
            {"name": "nginx:latest", "image": "docker.io/library/nginx:latest", "is_active": True},
            {"name": "redis:7-alpine", "image": "docker.io/library/redis:7-alpine", "is_active": True},
            {"name": "postgres:15", "image": "docker.io/library/postgres:15", "is_active": False}
        ]
        insert_result: OperationResult = self.image_ops.insert_many(images_data)
        self.assertTrue(insert_result.success)
        self.assertEqual(len(insert_result.data), 3)

        # Test find - should find all images
        find_result: OperationResult = self.image_ops.find({})
        self.assertTrue(find_result.success)
        self.assertEqual(len(find_result.data), 3)

        # Test find with filter - only active images
        find_active_result: OperationResult = self.image_ops.find({"is_active": True})
        self.assertTrue(find_active_result.success)
        self.assertEqual(len(find_active_result.data), 2)

        # Test find_one
        find_one_result: OperationResult = self.image_ops.find_one({"name": "nginx:latest"})
        self.assertTrue(find_one_result.success)
        self.assertEqual(find_one_result.data["name"], "nginx:latest")
        print('OK')

    def test_4_update_operations(self) -> None:
        '''
        Test case 4: update and update_many should work correctly.
        '''
        print('test_4_update_operations: ', end="")
        # Create images
        images_data: list = [
            {"name": "alpine:3.18", "image": "docker.io/library/alpine:3.18", "is_active": True},
            {"name": "node:18-alpine", "image": "docker.io/library/node:18-alpine", "is_active": True}
        ]
        insert_result: OperationResult = self.image_ops.insert_many(images_data)
        self.assertTrue(insert_result.success)

        # Test update - update single image
        update_result: OperationResult = self.image_ops.update(
            {"name": "alpine:3.18"},
            {"image": "docker.io/library/alpine:3.19"}
        )
        self.assertTrue(update_result.success)
        self.assertEqual(update_result.data["image"], "docker.io/library/alpine:3.19")

        # Test update_many - deactivate all images
        update_many_result: OperationResult = self.image_ops.update_many(
            {},
            {"is_active": False}
        )
        self.assertTrue(update_many_result.success)
        self.assertEqual(update_many_result.data["updated_count"], 2)

        # Verify all images are inactive
        find_result: OperationResult = self.image_ops.find({"is_active": True})
        self.assertTrue(find_result.success)
        self.assertEqual(len(find_result.data), 0)
        print('OK')

    def test_5_soft_delete_operations(self) -> None:
        '''
        Test case 5: soft_delete should set is_active to False.
        '''
        print('test_5_soft_delete_operations: ', end="")
        # Create image
        image_data: dict = {
            "name": "mariadb:10.11",
            "image": "docker.io/library/mariadb:10.11",
            "is_active": True
        }
        result: OperationResult = self.image_ops.insert(image_data)
        self.assertTrue(result.success)

        # Soft delete the image
        soft_delete_result: OperationResult = self.image_ops.soft_delete({"name": "mariadb:10.11"})
        self.assertTrue(soft_delete_result.success)

        # Verify the image is soft deleted
        find_result: OperationResult = self.image_ops.find_one({"name": "mariadb:10.11"})
        self.assertTrue(find_result.success)
        self.assertFalse(find_result.data["is_active"])
        print('OK')

    def test_6_soft_delete_many_operations(self) -> None:
        '''
        Test case 6: soft_delete_many should set is_active to False for multiple images.
        '''
        print('test_6_soft_delete_many_operations: ', end="")
        # Create multiple images
        images_data: list = [
            {"name": "mysql:8.0", "image": "docker.io/library/mysql:8.0", "is_active": True},
            {"name": "mongo:7.0", "image": "docker.io/library/mongo:7.0", "is_active": True}
        ]
        insert_result: OperationResult = self.image_ops.insert_many(images_data)
        self.assertTrue(insert_result.success)

        # Soft delete all images
        soft_delete_result: OperationResult = self.image_ops.soft_delete_many({})
        self.assertTrue(soft_delete_result.success)

        # Verify all images are soft deleted
        find_result: OperationResult = self.image_ops.find({"is_active": True})
        self.assertTrue(find_result.success)
        self.assertEqual(len(find_result.data), 0)

        # Verify images still exist
        find_all_result: OperationResult = self.image_ops.find({})
        self.assertTrue(find_all_result.success)
        self.assertEqual(len(find_all_result.data), 2)
        print('OK')

    def test_7_delete_operations(self) -> None:
        '''
        Test case 7: delete and delete_many should hard delete images.
        '''
        print('test_7_delete_operations: ', end="")
        # Create images
        images_data: list = [
            {"name": "rabbitmq:3.12", "image": "docker.io/library/rabbitmq:3.12", "is_active": True},
            {"name": "elasticsearch:8.11", "image": "docker.io/library/elasticsearch:8.11", "is_active": True},
            {"name": "kibana:8.11", "image": "docker.io/library/kibana:8.11", "is_active": True}
        ]
        insert_result: OperationResult = self.image_ops.insert_many(images_data)
        self.assertTrue(insert_result.success)

        # Hard delete one image
        delete_result: OperationResult = self.image_ops.delete({"name": "rabbitmq:3.12"})
        self.assertTrue(delete_result.success)

        # Verify it's deleted
        find_result: OperationResult = self.image_ops.find_one({"name": "rabbitmq:3.12"})
        self.assertFalse(find_result.success)

        # Hard delete remaining images
        delete_many_result: OperationResult = self.image_ops.delete_many({})
        self.assertTrue(delete_many_result.success)
        self.assertEqual(delete_many_result.data["deleted_count"], 2)

        # Verify all are deleted
        find_all_result: OperationResult = self.image_ops.find({})
        self.assertTrue(find_all_result.success)
        self.assertEqual(len(find_all_result.data), 0)
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
