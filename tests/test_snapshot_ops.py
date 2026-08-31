'''
Here in tests, we want to test the following:
1. Simple create snapshot with valid container should work - verify each field, including that
   containers.next_snapshot_sequence defaults to 1.
2. Duplicate (container_id, request_id) should fail (idempotency key).
3. Duplicate (container_id, version_sequence) should fail even with a different request_id.
4. The same (request_id, version_sequence) pair for two DIFFERENT containers should both succeed
   (uniqueness is scoped per-container, not global).
5. Create snapshot with invalid container_id should fail.
6. find/find_one/update should work correctly.
7. Deleting a container cascades to delete its snapshots (DB-level ON DELETE CASCADE - see the
   model's comment on why this can't rely on an ORM-level cascade alone).
'''

from dotenv import load_dotenv
from unittest import TestCase
import os

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from browseterm_db.operations.snapshot_ops import SnapshotOps
from browseterm_db.operations.container_ops import ContainerOps
from browseterm_db.operations.image_ops import ImageOps
from browseterm_db.operations.user_ops import UserOps
from browseterm_db.models.users import AuthProvider
from browseterm_db.models.containers import ContainerStatus
from browseterm_db.models.container_snapshots import SnapshotStatus
from browseterm_db.operations import OperationResult


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
        self.migrator.reset_database()
        self.migrator.reset_migrations()
        self.migrator.revision('Initial migration')
        self.migrator.upgrade()


class TestSnapshotOps(TestCase):
    '''
    Test the snapshot operations
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.snapshot_ops: SnapshotOps = SnapshotOps(self.db_config)
        self.container_ops: ContainerOps = ContainerOps(self.db_config)
        self.image_ops: ImageOps = ImageOps(self.db_config)
        self.user_ops: UserOps = UserOps(self.db_config)

    def tearDown(self) -> None:
        self.image_ops.delete_many({})

    def _make_user_and_container(self, email: str, container_name: str) -> tuple[str, str]:
        user_result: OperationResult = self.user_ops.insert({
            "email": email, "provider": AuthProvider.GOOGLE, "provider_id": email,
            "name": "Test User", "is_active": True,
        })
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]

        container_result: OperationResult = self.container_ops.insert({
            "user_id": user_id, "name": container_name, "status": ContainerStatus.RUNNING,
        })
        self.assertTrue(container_result.success, "Container creation should succeed")
        return user_id, container_result.data["id"]

    def test_1_simple_snapshot_creation_with_field_verification(self) -> None:
        print('test_1_simple_snapshot_creation_with_field_verification: ', end="")
        user_id, container_id = self._make_user_and_container("snap1@example.com", "snap-container-1")

        # next_snapshot_sequence defaults to 1 on a fresh container
        container_row = self.container_ops.find_one({"id": container_id}).data
        self.assertEqual(container_row["next_snapshot_sequence"], 1)

        snapshot_data: dict = {
            "container_id": container_id,
            "version_sequence": 1,
            "version": "0.0.0.0.1",
            "image_repository": "browseterm/u_c",
            "request_id": "req-1",
        }
        result: OperationResult = self.snapshot_ops.insert(snapshot_data)
        self.assertTrue(result.success, "Snapshot creation should succeed")
        self.assertEqual(result.data["container_id"], container_id)
        self.assertEqual(result.data["version_sequence"], 1)
        self.assertEqual(result.data["version"], "0.0.0.0.1")
        self.assertEqual(result.data["image_repository"], "browseterm/u_c")
        self.assertEqual(result.data["image_reference"], None)
        self.assertEqual(result.data["registry_digest"], None)
        self.assertEqual(result.data["request_id"], "req-1")
        self.assertEqual(result.data["status"], SnapshotStatus.PENDING.value)
        self.assertEqual(result.data["error_detail"], None)
        self.assertIsNotNone(result.data["created_at"])
        self.assertIsNotNone(result.data["updated_at"])
        self.assertEqual(result.data["completed_at"], None)

        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_2_duplicate_request_id_for_same_container_should_fail(self) -> None:
        print('test_2_duplicate_request_id_for_same_container_should_fail: ', end="")
        user_id, container_id = self._make_user_and_container("snap2@example.com", "snap-container-2")

        first = self.snapshot_ops.insert({
            "container_id": container_id, "version_sequence": 1, "version": "0.0.0.0.1",
            "image_repository": "browseterm/u_c", "request_id": "req-dup",
        })
        self.assertTrue(first.success)

        second = self.snapshot_ops.insert({
            "container_id": container_id, "version_sequence": 2, "version": "0.0.0.0.2",
            "image_repository": "browseterm/u_c", "request_id": "req-dup",  # same request_id
        })
        self.assertFalse(second.success, "Duplicate (container_id, request_id) should fail")

        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_3_duplicate_version_sequence_for_same_container_should_fail(self) -> None:
        print('test_3_duplicate_version_sequence_for_same_container_should_fail: ', end="")
        user_id, container_id = self._make_user_and_container("snap3@example.com", "snap-container-3")

        first = self.snapshot_ops.insert({
            "container_id": container_id, "version_sequence": 1, "version": "0.0.0.0.1",
            "image_repository": "browseterm/u_c", "request_id": "req-a",
        })
        self.assertTrue(first.success)

        second = self.snapshot_ops.insert({
            "container_id": container_id, "version_sequence": 1, "version": "0.0.0.0.1",  # same seq
            "image_repository": "browseterm/u_c", "request_id": "req-b",  # different request_id
        })
        self.assertFalse(second.success, "Duplicate (container_id, version_sequence) should fail")

        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_4_same_request_and_version_for_different_containers_both_succeed(self) -> None:
        print('test_4_same_request_and_version_for_different_containers_both_succeed: ', end="")
        user_id_a, container_id_a = self._make_user_and_container("snap4a@example.com", "snap-container-4a")
        user_id_b, container_id_b = self._make_user_and_container("snap4b@example.com", "snap-container-4b")

        result_a = self.snapshot_ops.insert({
            "container_id": container_id_a, "version_sequence": 1, "version": "0.0.0.0.1",
            "image_repository": "browseterm/u_c", "request_id": "shared-request-id",
        })
        result_b = self.snapshot_ops.insert({
            "container_id": container_id_b, "version_sequence": 1, "version": "0.0.0.0.1",
            "image_repository": "browseterm/u_c", "request_id": "shared-request-id",
        })
        self.assertTrue(result_a.success)
        self.assertTrue(result_b.success)

        self.user_ops.delete({"id": user_id_a})
        self.user_ops.delete({"id": user_id_b})
        print('OK')

    def test_5_snapshot_creation_with_invalid_container_should_fail(self) -> None:
        print('test_5_snapshot_creation_with_invalid_container_should_fail: ', end="")
        result = self.snapshot_ops.insert({
            "container_id": "00000000-0000-0000-0000-000000000000", "version_sequence": 1,
            "version": "0.0.0.0.1", "image_repository": "browseterm/u_c", "request_id": "req-x",
        })
        self.assertFalse(result.success, "Snapshot creation with a nonexistent container should fail")
        print('OK')

    def test_6_find_find_one_and_update(self) -> None:
        print('test_6_find_find_one_and_update: ', end="")
        user_id, container_id = self._make_user_and_container("snap6@example.com", "snap-container-6")

        self.snapshot_ops.insert({
            "container_id": container_id, "version_sequence": 1, "version": "0.0.0.0.1",
            "image_repository": "browseterm/u_c", "request_id": "req-6a",
        })
        second = self.snapshot_ops.insert({
            "container_id": container_id, "version_sequence": 2, "version": "0.0.0.0.2",
            "image_repository": "browseterm/u_c", "request_id": "req-6b",
        })
        self.assertTrue(second.success)
        snapshot_id = second.data["id"]

        find_result = self.snapshot_ops.find({"container_id": container_id})
        self.assertTrue(find_result.success)
        self.assertEqual(len(find_result.data), 2)

        find_one_result = self.snapshot_ops.find_one({"id": snapshot_id})
        self.assertTrue(find_one_result.success)
        self.assertEqual(find_one_result.data["id"], snapshot_id)

        update_result = self.snapshot_ops.update(
            {"id": snapshot_id},
            {"status": SnapshotStatus.SUCCEEDED, "registry_digest": "sha256:abc", "image_reference": "browseterm/u_c:0.0.0.0.2"},
        )
        self.assertTrue(update_result.success)
        updated = self.snapshot_ops.find_one({"id": snapshot_id}).data
        self.assertEqual(updated["status"], SnapshotStatus.SUCCEEDED.value)
        self.assertEqual(updated["registry_digest"], "sha256:abc")
        self.assertEqual(updated["image_reference"], "browseterm/u_c:0.0.0.0.2")

        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_7_deleting_container_cascades_to_snapshots(self) -> None:
        print('test_7_deleting_container_cascades_to_snapshots: ', end="")
        user_id, container_id = self._make_user_and_container("snap7@example.com", "snap-container-7")

        created = self.snapshot_ops.insert({
            "container_id": container_id, "version_sequence": 1, "version": "0.0.0.0.1",
            "image_repository": "browseterm/u_c", "request_id": "req-7",
        })
        self.assertTrue(created.success)
        snapshot_id = created.data["id"]

        # ContainerOps.delete() does a bulk query.delete() - bypasses ORM cascades entirely, so
        # this only works because of the DB-level ON DELETE CASCADE on container_snapshots.
        delete_result = self.container_ops.delete({"id": container_id})
        self.assertTrue(delete_result.success)

        find_result = self.snapshot_ops.find_one({"id": snapshot_id})
        self.assertTrue(find_result.success)
        self.assertEqual(find_result.data, None, "Snapshot should be gone via ON DELETE CASCADE")

        self.user_ops.delete({"id": user_id})
        print('OK')
