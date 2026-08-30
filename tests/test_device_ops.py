'''
Here in tests, we want to test the following:
1. Simple create device with valid user should work. We verify each field once the device is created.
2. Create device with invalid user should fail.
3. Duplicate device_name for the same user should fail (unique constraint).
4. The same device_name for two different users should both succeed.
5. status should default to Active and used_* counters should default to 0.
6. find and find_one should work correctly.
7. update should work correctly (including setting last_seen_at / status).
8. delete should hard delete a device.
9. A new user should have 0 devices, and deleting a user should cascade-delete their devices.
'''

# builtins
import os
from unittest import TestCase
import uuid

# third party
from dotenv import load_dotenv

# local
from browseterm_db.operations.device_ops import DeviceOps
from browseterm_db.operations.user_ops import UserOps
from browseterm_db.operations import OperationResult
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from browseterm_db.models.users import AuthProvider
from browseterm_db.models.devices import DeviceStatus


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


class TestDeviceOps(TestCase):
    '''
    All tests for DeviceOps
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.device_ops: DeviceOps = DeviceOps(self.db_config)
        self.user_ops: UserOps = UserOps(self.db_config)

    def _create_user(self, email: str, provider_id: str) -> dict:
        '''Helper: create a user and return its dict.'''
        user_data: dict = {
            "email": email,
            "provider": AuthProvider.GOOGLE,
            "provider_id": provider_id,
            "name": "Test User",
            "is_active": True,
        }
        result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(result.success, f"User creation failed: {result.error}")
        return result.data

    def test_1_simple_device_creation_with_field_verification(self) -> None:
        '''
        Test case 1: Simple create device with valid user should work. We verify each field once the device is created.
        '''
        print('test_1_simple_device_creation_with_field_verification: ', end="")
        user: dict = self._create_user("device_user1@example.com", "google_device_1")

        device_data: dict = {
            "user_id": user["id"],
            "device_name": "Namah's MacBook Pro",
            "os": "macOS",
            "architecture": "arm64",
            "runtime_version": "0.1.0",
            "total_cpu": 8,
            "total_memory_bytes": 17179869184,
            "total_storage_bytes": 512000000000,
            "allocated_cpu": 4,
            "allocated_memory_bytes": 8589934592,
            "allocated_storage_bytes": 100000000000,
            "gpu_info": {"name": "Apple M2", "cores": 10},
        }
        result: OperationResult = self.device_ops.insert(device_data)
        self.assertTrue(result.success, f"Device creation failed: {result.error}")
        self.assertEqual(result.message, "Device created successfully")

        created_device: dict = result.data
        self.assertIsNotNone(created_device)
        self.assertEqual(created_device["user_id"], user["id"])
        self.assertEqual(created_device["device_name"], device_data["device_name"])
        self.assertEqual(created_device["os"], device_data["os"])
        self.assertEqual(created_device["architecture"], device_data["architecture"])
        self.assertEqual(created_device["runtime_version"], device_data["runtime_version"])
        self.assertEqual(created_device["total_cpu"], device_data["total_cpu"])
        self.assertEqual(created_device["total_memory_bytes"], device_data["total_memory_bytes"])
        self.assertEqual(created_device["total_storage_bytes"], device_data["total_storage_bytes"])
        self.assertEqual(created_device["allocated_cpu"], device_data["allocated_cpu"])
        self.assertEqual(created_device["allocated_memory_bytes"], device_data["allocated_memory_bytes"])
        self.assertEqual(created_device["allocated_storage_bytes"], device_data["allocated_storage_bytes"])
        self.assertEqual(created_device["gpu_info"], device_data["gpu_info"])

        # Verify UUID is generated
        self.assertIsNotNone(created_device["id"])
        uuid.UUID(created_device["id"])

        # Verify used_* counters default to 0
        self.assertEqual(created_device["used_cpu"], 0)
        self.assertEqual(created_device["used_memory_bytes"], 0)
        self.assertEqual(created_device["used_storage_bytes"], 0)

        # Verify status defaults to Active
        self.assertEqual(created_device["status"], DeviceStatus.ACTIVE.value)

        # Verify timestamps
        self.assertIsNotNone(created_device["registered_at"])
        self.assertIsNotNone(created_device["updated_at"])
        self.assertIsNone(created_device["last_seen_at"])
        self.assertIsNone(created_device["revoked_at"])

        # Verify we can find the device
        find_result: OperationResult = self.device_ops.find_one({"id": created_device["id"]})
        self.assertTrue(find_result.success)
        self.assertEqual(find_result.data["id"], created_device["id"])

        # cleanup
        self.device_ops.delete({"id": created_device["id"]})
        self.user_ops.delete({"id": user["id"]})
        print('OK')

    def test_2_device_creation_with_invalid_user_should_fail(self) -> None:
        '''
        Test case 2: Create device with invalid (nonexistent) user should fail.
        '''
        print('test_2_device_creation_with_invalid_user_should_fail: ', end="")
        device_data: dict = {
            "user_id": str(uuid.uuid4()),
            "device_name": "Orphan Device",
            "os": "macOS",
            "architecture": "arm64",
            "total_cpu": 4,
            "total_memory_bytes": 8589934592,
            "total_storage_bytes": 100000000000,
            "allocated_cpu": 2,
            "allocated_memory_bytes": 4294967296,
            "allocated_storage_bytes": 50000000000,
        }
        result: OperationResult = self.device_ops.insert(device_data)
        self.assertFalse(result.success, "Device creation with invalid user should fail")
        print('OK')

    def test_3_duplicate_device_name_same_user_should_fail(self) -> None:
        '''
        Test case 3: Duplicate device_name for the same user should fail (unique constraint).
        '''
        print('test_3_duplicate_device_name_same_user_should_fail: ', end="")
        user: dict = self._create_user("device_user3@example.com", "google_device_3")
        device_data: dict = {
            "user_id": user["id"],
            "device_name": "Shared Name",
            "os": "macOS",
            "architecture": "arm64",
            "total_cpu": 4,
            "total_memory_bytes": 8589934592,
            "total_storage_bytes": 100000000000,
            "allocated_cpu": 2,
            "allocated_memory_bytes": 4294967296,
            "allocated_storage_bytes": 50000000000,
        }
        result1: OperationResult = self.device_ops.insert(device_data)
        self.assertTrue(result1.success, "First device creation should succeed")

        result2: OperationResult = self.device_ops.insert(device_data)
        self.assertFalse(result2.success, "Duplicate device_name for the same user should fail")

        # cleanup
        self.device_ops.delete({"id": result1.data["id"]})
        self.user_ops.delete({"id": user["id"]})
        print('OK')

    def test_4_same_device_name_different_users_should_succeed(self) -> None:
        '''
        Test case 4: The same device_name for two different users should both succeed.
        '''
        print('test_4_same_device_name_different_users_should_succeed: ', end="")
        user_a: dict = self._create_user("device_user4a@example.com", "google_device_4a")
        user_b: dict = self._create_user("device_user4b@example.com", "google_device_4b")

        base_device: dict = {
            "device_name": "MacBook Pro",
            "os": "macOS",
            "architecture": "arm64",
            "total_cpu": 4,
            "total_memory_bytes": 8589934592,
            "total_storage_bytes": 100000000000,
            "allocated_cpu": 2,
            "allocated_memory_bytes": 4294967296,
            "allocated_storage_bytes": 50000000000,
        }
        result_a: OperationResult = self.device_ops.insert({**base_device, "user_id": user_a["id"]})
        self.assertTrue(result_a.success)
        result_b: OperationResult = self.device_ops.insert({**base_device, "user_id": user_b["id"]})
        self.assertTrue(result_b.success)

        # cleanup
        self.device_ops.delete({"id": result_a.data["id"]})
        self.device_ops.delete({"id": result_b.data["id"]})
        self.user_ops.delete({"id": user_a["id"]})
        self.user_ops.delete({"id": user_b["id"]})
        print('OK')

    def test_5_find_and_update(self) -> None:
        '''
        Test case 5: find/find_one filters and update (last_seen_at, status, used_* counters).
        '''
        print('test_5_find_and_update: ', end="")
        user: dict = self._create_user("device_user5@example.com", "google_device_5")
        device_data: dict = {
            "user_id": user["id"],
            "device_name": "Update Target",
            "os": "macOS",
            "architecture": "arm64",
            "total_cpu": 8,
            "total_memory_bytes": 17179869184,
            "total_storage_bytes": 512000000000,
            "allocated_cpu": 4,
            "allocated_memory_bytes": 8589934592,
            "allocated_storage_bytes": 100000000000,
        }
        result: OperationResult = self.device_ops.insert(device_data)
        self.assertTrue(result.success)
        device_id: str = result.data["id"]

        # find by user_id
        find_result: OperationResult = self.device_ops.find({"user_id": user["id"]})
        self.assertTrue(find_result.success)
        self.assertEqual(len(find_result.data), 1)

        # update used_cpu / status / last_seen_at
        from datetime import datetime, timezone
        heartbeat_time: str = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        update_result: OperationResult = self.device_ops.update(
            {"id": device_id},
            {"used_cpu": 2, "status": DeviceStatus.INACTIVE, "last_seen_at": heartbeat_time}
        )
        self.assertTrue(update_result.success)

        find_one_result: OperationResult = self.device_ops.find_one({"id": device_id})
        self.assertTrue(find_one_result.success)
        self.assertEqual(find_one_result.data["used_cpu"], 2)
        self.assertEqual(find_one_result.data["status"], DeviceStatus.INACTIVE.value)
        self.assertEqual(find_one_result.data["last_seen_at"], heartbeat_time)

        # cleanup
        self.device_ops.delete({"id": device_id})
        self.user_ops.delete({"id": user["id"]})
        print('OK')

    def test_6_new_user_has_zero_devices_and_cascade_delete(self) -> None:
        '''
        Test case 6: A new user should have 0 devices, and deleting a user should cascade-delete their devices.
        '''
        print('test_6_new_user_has_zero_devices_and_cascade_delete: ', end="")
        user: dict = self._create_user("device_user6@example.com", "google_device_6")

        devices_result: OperationResult = self.device_ops.find({"user_id": user["id"]})
        self.assertTrue(devices_result.success)
        self.assertEqual(len(devices_result.data), 0, "New user should have 0 devices")

        device_data: dict = {
            "user_id": user["id"],
            "device_name": "Cascade Device",
            "os": "macOS",
            "architecture": "arm64",
            "total_cpu": 4,
            "total_memory_bytes": 8589934592,
            "total_storage_bytes": 100000000000,
            "allocated_cpu": 2,
            "allocated_memory_bytes": 4294967296,
            "allocated_storage_bytes": 50000000000,
        }
        create_result: OperationResult = self.device_ops.insert(device_data)
        self.assertTrue(create_result.success)

        # deleting the user should cascade-delete the device (delete-orphan relationship)
        self.user_ops.delete({"id": user["id"]})

        find_result: OperationResult = self.device_ops.find_one({"id": create_result.data["id"]})
        self.assertTrue(find_result.success)
        self.assertIsNone(find_result.data, "Device should be gone after owning user is deleted")
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
