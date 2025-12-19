'''
Here in tests, we want to test the following:
1. Simple create container with valid user should work. We will verify each field once the container is created.
2. Create container with invalid user should fail.
3. Duplicate container creation should Fail.
4. Container with invalid status should fail.
'''


from dotenv import load_dotenv
from unittest import TestCase
import os

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from browseterm_db.operations.container_ops import ContainerOps
from browseterm_db.operations.image_ops import ImageOps
from browseterm_db.operations.user_ops import UserOps
from browseterm_db.models.users import AuthProvider
from browseterm_db.operations import OperationResult
from browseterm_db.models.containers import ContainerStatus


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


class TestContainerOps(TestCase):
    '''
    Test the container operations
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.container_ops: ContainerOps = ContainerOps(self.db_config)
        self.image_ops: ImageOps = ImageOps(self.db_config)
        self.user_ops: UserOps = UserOps(self.db_config)

    def tearDown(self) -> None:
        """Clean up all images after each test"""
        self.image_ops.delete_many({})

    def test_1_simple_container_creation_with_field_verification(self) -> None:
        '''
        Test case 1: Simple create container with valid user should work. We will verify each field once the container is created.
        '''
        print('test_1_simple_container_creation_with_field_verification: ', end="")
        # Create a user
        user_data: dict = {
            "email": "duplicate@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_456",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        # verify the user is created
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]

        # create an image
        image_data: dict = {
            "name": "python:3.12-slim",
            "image": "docker.io/library/python:3.12-slim",
            "is_active": True
        }
        image_result: OperationResult = self.image_ops.insert(image_data)
        self.assertTrue(image_result.success, "Image creation should succeed")
        image_id: str = image_result.data["id"]

        # create a container
        container_data: dict = {
            "user_id": user_id,
            "image_id": image_id,
            "name": "test-container",
            "status": ContainerStatus.RUNNING,
            "ip_address": "127.0.0.1"
        }
        container_result: OperationResult = self.container_ops.insert(container_data)
        # verify the container is created
        self.assertTrue(container_result.success, "Container creation should succeed")
        # verify the container is created with the correct fields
        self.assertEqual(container_result.data["user_id"], user_id)
        self.assertEqual(container_result.data["image_id"], image_id)
        self.assertEqual(container_result.data["name"], container_data["name"])
        self.assertEqual(container_result.data["status"], container_data["status"].value)
        self.assertEqual(container_result.data["cpu_limit"], '1')  # default value should be 1
        self.assertEqual(container_result.data["memory_limit"], '1Gi')  # default value should be 1Gi
        self.assertEqual(container_result.data["storage_limit"], '2Gi')  # default value should be 2Gi
        self.assertEqual(container_result.data["ip_address"], "127.0.0.1")  # should match the provided value
        self.assertEqual(container_result.data["port_mappings"], None)  # default value should be None
        self.assertEqual(container_result.data["environment_vars"], None)  # default value should be None
        self.assertEqual(container_result.data["associated_resources"], None)  # default value should be None
        self.assertEqual(container_result.data["created_at"] is not None, True)  # created_at should be not None
        self.assertEqual(container_result.data["updated_at"] is not None, True)  # updated_at should be not None
        self.assertEqual(container_result.data["deleted_at"], None)  # deleted_at should be None
        self.assertEqual(container_result.data["kubernetes_id"], None)  # kubernetes_id should be None by default
        self.assertEqual(container_result.data["saved_image"], None)  # saved_image should be None by default
        # delete the user
        delete_result: OperationResult = self.user_ops.delete({"id": user_id})
        self.assertTrue(delete_result.success, "User deletion should succeed")
        # find the container: The container should not exist because of ON DELETE CASCADE
        find_result: OperationResult = self.container_ops.find_one({"id": container_result.data["id"]})
        self.assertTrue(find_result.success, "Container should not exist due to ON DELETE CASCADE")
        self.assertEqual(find_result.data, None)
        print('OK')

    def test_2_container_creation_with_invalid_user_should_fail(self) -> None:
        '''
        Test case 2: Create container with invalid user should fail.
        '''
        print('test_2_container_creation_with_invalid_user_should_fail: ', end="")
        # Create an image
        image_data: dict = {
            "name": "python:3.12-slim",
            "image": "docker.io/library/python:3.12-slim",
            "is_active": True
        }
        image_result: OperationResult = self.image_ops.insert(image_data)
        self.assertTrue(image_result.success, "Image creation should succeed")
        image_id: str = image_result.data["id"]

        # Create a container with invalid user
        container_data: dict = {
            "user_id": "invalid_user_id",
            "image_id": image_id,
            "name": "test-container",
            "status": ContainerStatus.RUNNING,
            "ip_address": "127.0.0.1"
        }
        container_result: OperationResult = self.container_ops.insert(container_data)
        self.assertFalse(container_result.success, "Container creation should fail")

        # Clean up image
        self.image_ops.delete({"id": image_id})
        print('OK')

    def test_3_duplicate_container_creation_should_fail(self) -> None:
        '''
        Test case 3: Duplicate container creation should fail.
        '''
        print('test_3_duplicate_container_creation_should_fail: ', end="")
        # Create a user
        user_data: dict = {
            "email": "duplicate@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_456",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        # verify the user is created
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]

        # create an image
        image_data: dict = {
            "name": "python:3.12-slim",
            "image": "docker.io/library/python:3.12-slim",
            "is_active": True
        }
        image_result: OperationResult = self.image_ops.insert(image_data)
        self.assertTrue(image_result.success, "Image creation should succeed")
        image_id: str = image_result.data["id"]

        # create a container
        container_data: dict = {
            "user_id": user_id,
            "image_id": image_id,
            "name": "test-container",
            "status": ContainerStatus.RUNNING,
            "ip_address": "127.0.0.1"
        }
        container_result: OperationResult = self.container_ops.insert(container_data)
        # verify the container is created
        self.assertTrue(container_result.success, "Container creation should succeed")
        # create a duplicate container
        duplicate_container_result: OperationResult = self.container_ops.insert(container_data)
        self.assertFalse(duplicate_container_result.success, "Duplicate container creation should fail")
        # delete the user
        self.user_ops.delete({"id": user_id})
        # delete the container
        find_result: OperationResult = self.container_ops.find_one({"id": container_result.data["id"]})
        self.assertTrue(find_result.success, "Container should not exist due on ON DELETE CASCADE")
        self.assertEqual(find_result.data, None)
        print('OK')

    def test_4_container_creation_with_invalid_status_should_fail(self) -> None:
        '''
        Test case 4: Create container with invalid status should fail.
        '''
        print('test_4_container_creation_with_invalid_status_should_fail: ', end="")
        # Create a user
        user_data: dict = {
            "email": "invalid_status@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_456",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        # verify the user is created
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]

        # create an image
        image_data: dict = {
            "name": "python:3.12-slim",
            "image": "docker.io/library/python:3.12-slim",
            "is_active": True
        }
        image_result: OperationResult = self.image_ops.insert(image_data)
        self.assertTrue(image_result.success, "Image creation should succeed")
        image_id: str = image_result.data["id"]

        # create a container with invalid status
        container_data: dict = {
            "user_id": user_id,
            "image_id": image_id,
            "name": "test-container",
            "status": "Invalid",
            "ip_address": "127.0.0.1"
        }
        container_result: OperationResult = self.container_ops.insert(container_data)
        self.assertFalse(container_result.success, "Container creation should fail")
        # delete the user
        delete_result: OperationResult = self.user_ops.delete({"id": user_id})
        self.assertTrue(delete_result.success, "User deletion should succeed")
        # the container never got created, so it should not exist
        print('OK')

    def test_5_container_delete_should_not_delete_user(self) -> None:
        '''
        Test case 5: Delete container should not delete user.
        '''
        print('test_5_container_delete_should_not_delete_user: ', end="")
        # Create a user
        user_data: dict = {
            "email": "delete_user@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_456",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        # verify the user is created
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]

        # create an image
        image_data: dict = {
            "name": "python:3.12-slim",
            "image": "docker.io/library/python:3.12-slim",
            "is_active": True
        }
        image_result: OperationResult = self.image_ops.insert(image_data)
        self.assertTrue(image_result.success, "Image creation should succeed")
        image_id: str = image_result.data["id"]

        # create a container
        container_data: dict = {
            "user_id": user_id,
            "image_id": image_id,
            "name": "test-container",
            "status": ContainerStatus.RUNNING,
            "ip_address": "127.0.0.1"
        }
        container_result: OperationResult = self.container_ops.insert(container_data)
        # verify the container is created
        self.assertTrue(container_result.success, "Container creation should succeed")
        # delete the container
        delete_result: OperationResult = self.container_ops.delete({"id": container_result.data["id"]})
        self.assertTrue(delete_result.success, "Container deletion should succeed")
        # should not be able to find the container
        container_find_result: OperationResult = self.container_ops.find_one({"id": container_result.data["id"]})
        self.assertTrue(container_find_result.success, "Container should be deleted")
        self.assertEqual(container_find_result.data, None)
        # find the user: The user should still exist
        user_find_result: OperationResult = self.user_ops.find_one({"id": user_id})
        self.assertTrue(user_find_result.success, "User should still exist")
        self.assertEqual(user_find_result.data["is_active"], True)
        # delete the user
        delete_user_result: OperationResult = self.user_ops.delete({"id": user_id})
        self.assertTrue(delete_user_result.success, "User deletion should succeed")
        print('OK')


class ZZZ_Cleanup(TestCase):
    '''
    Cleanup: Delete all tables.
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
