'''
Tests for DeviceCommandOps, covering the Part 1 transactional invariants
(BROWSETERM_CLOUD_CONTROL_PLANE_MIGRATION.md):

1. Two simultaneous activation requests still leave exactly one active device.
2. Two simultaneous resume/create requests cannot over-reserve quota.
3. Duplicate quota release does not make counters negative.
4. Old placement generation cannot update a moved container.
5. Only one active lifecycle command can exist for a container.
6. Insufficient quota / offline device / wrong-user device are rejected up front.
'''

# builtins
import os
import threading
import uuid
from unittest import TestCase

# third party
from dotenv import load_dotenv

# local
from browseterm_db.operations.device_command_ops import DeviceCommandOps
from browseterm_db.operations.device_ops import DeviceOps
from browseterm_db.operations.container_ops import ContainerOps
from browseterm_db.operations.user_ops import UserOps
from browseterm_db.operations import OperationResult
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from browseterm_db.models.users import AuthProvider
from browseterm_db.models.devices import DeviceStatus
from browseterm_db.models.device_commands import CommandOperation, CommandStatus


load_dotenv('.env')


def _db_config() -> DBConfig:
    return DBConfig(
        username=os.getenv('TEST_DB_USERNAME'),
        password=os.getenv('TEST_DB_PASSWORD'),
        host=os.getenv('TEST_DB_HOST'),
        port=int(os.getenv('TEST_DB_PORT')),
        database=os.getenv('TEST_DB_DATABASE'),
    )


class AAA_InitialSetup(TestCase):
    '''Initial database setup - same pattern as test_device_ops.py.'''

    def setUp(self) -> None:
        self.db_config: DBConfig = _db_config()
        self.migrator: Migrator = Migrator(self.db_config, TEST_MIGRATIONS_DIR, versions_subdir="test_versions")

    def test_setup(self) -> None:
        self.migrator.reset_database()
        self.migrator.reset_migrations()
        self.migrator.revision('Initial migration')
        self.migrator.upgrade()


class TestDeviceCommandOps(TestCase):
    '''All tests for DeviceCommandOps.'''

    def setUp(self) -> None:
        self.db_config: DBConfig = _db_config()
        self.command_ops: DeviceCommandOps = DeviceCommandOps(self.db_config)
        self.device_ops: DeviceOps = DeviceOps(self.db_config)
        self.container_ops: ContainerOps = ContainerOps(self.db_config)
        self.user_ops: UserOps = UserOps(self.db_config)

    def _create_user(self, email: str, provider_id: str) -> dict:
        result: OperationResult = self.user_ops.insert({
            "email": email, "provider": AuthProvider.GOOGLE, "provider_id": provider_id, "name": "Test User",
        })
        self.assertTrue(result.success, f"User creation failed: {result.error}")
        return result.data

    def _create_device(self, user_id: str, name: str, allocated_cpu: int = 4,
                        allocated_memory_bytes: int = 8_589_934_592, allocated_storage_bytes: int = 100_000_000_000) -> dict:
        result: OperationResult = self.device_ops.insert({
            "user_id": user_id, "device_name": name, "os": "macOS", "architecture": "arm64",
            "total_cpu": 8, "total_memory_bytes": 17_179_869_184, "total_storage_bytes": 512_000_000_000,
            "allocated_cpu": allocated_cpu, "allocated_memory_bytes": allocated_memory_bytes,
            "allocated_storage_bytes": allocated_storage_bytes,
        })
        self.assertTrue(result.success, f"Device creation failed: {result.error}")
        return result.data

    def _create_container(self, user_id: str, name: str) -> dict:
        result: OperationResult = self.container_ops.insert({"user_id": user_id, "name": name})
        self.assertTrue(result.success, f"Container creation failed: {result.error}")
        return result.data

    # ---- 1. Atomic activation -------------------------------------------------------------------

    def test_1_activate_device_sets_active_device_id(self) -> None:
        print('test_1_activate_device_sets_active_device_id: ', end="")
        user = self._create_user("cmd_user1@example.com", "google_cmd_1")
        device = self._create_device(user["id"], "Device A")
        result = self.command_ops.activate_device(user["id"], device["id"])
        self.assertTrue(result.success, f"Activation failed: {result.error}")
        updated_user = self.user_ops.find_one({"id": user["id"]})
        self.assertEqual(updated_user.data["active_device_id"], device["id"])
        print('OK')

    def test_2_activate_device_rejects_device_belonging_to_another_user(self) -> None:
        print('test_2_activate_device_rejects_device_belonging_to_another_user: ', end="")
        user1 = self._create_user("cmd_user2a@example.com", "google_cmd_2a")
        user2 = self._create_user("cmd_user2b@example.com", "google_cmd_2b")
        device2 = self._create_device(user2["id"], "User2 Device")
        result = self.command_ops.activate_device(user1["id"], device2["id"])
        self.assertFalse(result.success, "Activating another user's device should fail")
        print('OK')

    def test_3_two_simultaneous_activations_leave_exactly_one_active_device(self) -> None:
        '''Doc-required test: two simultaneous activation requests still leave exactly one active device.'''
        print('test_3_two_simultaneous_activations_leave_exactly_one_active_device: ', end="")
        user = self._create_user("cmd_user3@example.com", "google_cmd_3")
        device_a = self._create_device(user["id"], "Device A3")
        device_b = self._create_device(user["id"], "Device B3")

        results = [None, None]

        def _activate(index: int, device_id: str) -> None:
            ops = DeviceCommandOps(_db_config())  # separate session per thread, real concurrency
            results[index] = ops.activate_device(user["id"], device_id)

        t1 = threading.Thread(target=_activate, args=(0, device_a["id"]))
        t2 = threading.Thread(target=_activate, args=(1, device_b["id"]))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertTrue(results[0].success and results[1].success, "Both activation calls should succeed individually")
        final_user = self.user_ops.find_one({"id": user["id"]})
        self.assertIn(final_user.data["active_device_id"], (device_a["id"], device_b["id"]))
        print('OK')

    # ---- 2/6. Quota reservation -------------------------------------------------------------------

    def test_4_reserve_quota_and_create_command_happy_path(self) -> None:
        print('test_4_reserve_quota_and_create_command_happy_path: ', end="")
        user = self._create_user("cmd_user4@example.com", "google_cmd_4")
        device = self._create_device(user["id"], "Device 4", allocated_cpu=4, allocated_memory_bytes=8_589_934_592, allocated_storage_bytes=100_000_000_000)
        self.command_ops.activate_device(user["id"], device["id"])
        container = self._create_container(user["id"], "workspace-4")

        result = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=1, memory_bytes=1_073_741_824, storage_bytes=2_000_000_000,
        )
        self.assertTrue(result.success, f"Reservation failed: {result.error}")
        self.assertEqual(result.data["status"], CommandStatus.QUEUED.value)
        self.assertEqual(result.data["placement_generation"], 1)

        updated_device = self.device_ops.find_one({"id": device["id"]})
        self.assertEqual(updated_device.data["reserved_cpu"], 1)
        self.assertEqual(updated_device.data["reserved_memory_bytes"], 1_073_741_824)

        updated_container = self.container_ops.find_one({"id": container["id"]})
        self.assertEqual(updated_container.data["placement_generation"], 1)
        self.assertEqual(updated_container.data["device_id"], device["id"])
        print('OK')

    def test_5_reserve_quota_rejects_insufficient_capacity(self) -> None:
        print('test_5_reserve_quota_rejects_insufficient_capacity: ', end="")
        user = self._create_user("cmd_user5@example.com", "google_cmd_5")
        device = self._create_device(user["id"], "Device 5", allocated_cpu=2, allocated_memory_bytes=2_000_000_000, allocated_storage_bytes=10_000_000_000)
        self.command_ops.activate_device(user["id"], device["id"])
        container = self._create_container(user["id"], "workspace-5")

        result = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=99, memory_bytes=1, storage_bytes=1,
        )
        self.assertFalse(result.success)
        self.assertIn("quota", result.error.lower())
        print('OK')

    def test_6_reserve_quota_rejects_non_active_device(self) -> None:
        print('test_6_reserve_quota_rejects_non_active_device: ', end="")
        user = self._create_user("cmd_user6@example.com", "google_cmd_6")
        device = self._create_device(user["id"], "Device 6")
        # never activated - user.active_device_id is still None
        container = self._create_container(user["id"], "workspace-6")

        result = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=1, memory_bytes=1, storage_bytes=1,
        )
        self.assertFalse(result.success)
        print('OK')

    def test_7_two_simultaneous_reservations_cannot_over_reserve_quota(self) -> None:
        '''Doc-required test: two simultaneous resume/create requests cannot over-reserve quota.'''
        print('test_7_two_simultaneous_reservations_cannot_over_reserve_quota: ', end="")
        user = self._create_user("cmd_user7@example.com", "google_cmd_7")
        # Exactly enough capacity for ONE of the two 3-cpu requests, never both (4 total).
        device = self._create_device(user["id"], "Device 7", allocated_cpu=4, allocated_memory_bytes=8_589_934_592, allocated_storage_bytes=100_000_000_000)
        self.command_ops.activate_device(user["id"], device["id"])
        container_a = self._create_container(user["id"], "workspace-7a")
        container_b = self._create_container(user["id"], "workspace-7b")

        results = [None, None]

        def _reserve(index: int, container_id: str) -> None:
            ops = DeviceCommandOps(_db_config())
            results[index] = ops.reserve_quota_and_create_command(
                user_id=user["id"], device_id=device["id"], container_id=container_id,
                operation=CommandOperation.CREATE, cpu=3, memory_bytes=1, storage_bytes=1,
            )

        t1 = threading.Thread(target=_reserve, args=(0, container_a["id"]))
        t2 = threading.Thread(target=_reserve, args=(1, container_b["id"]))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        self.assertEqual(len(successes), 1, "Exactly one of the two 3-cpu reservations should succeed on a 4-cpu device")
        self.assertEqual(len(failures), 1)

        final_device = self.device_ops.find_one({"id": device["id"]})
        self.assertEqual(final_device.data["reserved_cpu"], 3, "Only the winning reservation's quota should be held")
        print('OK')

    # ---- 3. Exactly-once quota release --------------------------------------------------------

    def test_8_duplicate_quota_release_does_not_go_negative(self) -> None:
        print('test_8_duplicate_quota_release_does_not_go_negative: ', end="")
        user = self._create_user("cmd_user8@example.com", "google_cmd_8")
        device = self._create_device(user["id"], "Device 8")
        self.command_ops.activate_device(user["id"], device["id"])
        container = self._create_container(user["id"], "workspace-8")

        reserve_result = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=2, memory_bytes=1, storage_bytes=1,
        )
        self.assertTrue(reserve_result.success)
        command_id = reserve_result.data["id"]

        first_release = self.command_ops.release_quota_for_command(command_id)
        self.assertTrue(first_release.success)
        self.assertFalse(first_release.data["already_released"])

        second_release = self.command_ops.release_quota_for_command(command_id)
        self.assertTrue(second_release.success)
        self.assertTrue(second_release.data["already_released"])

        final_device = self.device_ops.find_one({"id": device["id"]})
        self.assertEqual(final_device.data["reserved_cpu"], 0, "Quota must not be released twice")
        self.assertGreaterEqual(final_device.data["reserved_cpu"], 0, "Reserved quota must never go negative")
        print('OK')

    # ---- 4. Conditional container update by placement generation ------------------------------

    def test_9_stale_placement_generation_is_rejected(self) -> None:
        '''Doc-required test: old placement generation cannot update a moved container.'''
        print('test_9_stale_placement_generation_is_rejected: ', end="")
        user = self._create_user("cmd_user9@example.com", "google_cmd_9")
        device_a = self._create_device(user["id"], "Device 9A")
        device_b = self._create_device(user["id"], "Device 9B")
        container = self._create_container(user["id"], "workspace-9")

        self.command_ops.activate_device(user["id"], device_a["id"])
        reserve_a = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device_a["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=1, memory_bytes=1, storage_bytes=1,
        )
        self.assertTrue(reserve_a.success)
        stale_generation = reserve_a.data["placement_generation"]  # 1
        # The first command must finish before a second lifecycle command for the same container
        # can be created (the "only one active command per container" invariant, tested
        # separately in test_10) - mark it SUCCEEDED, mirroring what a real CommandResult would do.
        self.command_ops.update({"id": reserve_a.data["id"]}, {"status": CommandStatus.SUCCEEDED})

        # Container moves to device B: activate B, then Resume there bumps placement_generation
        # to 2 (reserve_quota_and_create_command bumps containers.placement_generation itself).
        self.command_ops.activate_device(user["id"], device_b["id"])
        reserve_b = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device_b["id"], container_id=container["id"],
            operation=CommandOperation.RESUME, cpu=1, memory_bytes=1, storage_bytes=1,
        )
        self.assertTrue(reserve_b.success, f"Second reservation failed: {reserve_b.error if reserve_b else None}")
        current_generation = reserve_b.data["placement_generation"]  # 2
        self.assertGreater(current_generation, stale_generation)

        # A late result from the OLD command (device A, stale generation) must be a no-op.
        stale_update = self.command_ops.conditional_container_update(
            container_id=container["id"], expected_device_id=device_a["id"],
            expected_placement_generation=stale_generation, update_data={"kubernetes_id": "stale-pod-id"},
        )
        self.assertTrue(stale_update.success)
        self.assertEqual(stale_update.data["matched"], 0, "A stale placement generation must not match any row")

        current_container = self.container_ops.find_one({"id": container["id"]})
        self.assertIsNone(current_container.data["kubernetes_id"], "Stale update must not have applied")

        # A fresh result at the CURRENT generation/device must apply.
        fresh_update = self.command_ops.conditional_container_update(
            container_id=container["id"], expected_device_id=device_b["id"],
            expected_placement_generation=current_generation, update_data={"kubernetes_id": "fresh-pod-id"},
        )
        self.assertEqual(fresh_update.data["matched"], 1)
        current_container = self.container_ops.find_one({"id": container["id"]})
        self.assertEqual(current_container.data["kubernetes_id"], "fresh-pod-id")
        print('OK')

    # ---- 5. At most one active command per container -------------------------------------------

    def test_10_only_one_active_command_per_container(self) -> None:
        '''Doc-required test: only one active lifecycle command can exist for a container.'''
        print('test_10_only_one_active_command_per_container: ', end="")
        user = self._create_user("cmd_user10@example.com", "google_cmd_10")
        device = self._create_device(user["id"], "Device 10", allocated_cpu=8)
        self.command_ops.activate_device(user["id"], device["id"])
        container = self._create_container(user["id"], "workspace-10")

        first = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=1, memory_bytes=1, storage_bytes=1,
        )
        self.assertTrue(first.success)

        second = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=1, memory_bytes=1, storage_bytes=1,
        )
        self.assertFalse(second.success, "A second active command for the same container must be rejected")

        # The failed second attempt's quota must have been rolled back entirely, not partially.
        final_device = self.device_ops.find_one({"id": device["id"]})
        self.assertEqual(final_device.data["reserved_cpu"], 1, "Rejected second reservation must not leak reserved quota")

        commands = self.command_ops.find({"container_id": container["id"]})
        active = [c for c in commands.data if c["status"] in ("Queued", "Delivered", "Accepted", "Running")]
        self.assertEqual(len(active), 1)
        print('OK')

    def test_11_new_active_command_allowed_after_prior_one_completes(self) -> None:
        print('test_11_new_active_command_allowed_after_prior_one_completes: ', end="")
        user = self._create_user("cmd_user11@example.com", "google_cmd_11")
        device = self._create_device(user["id"], "Device 11", allocated_cpu=8)
        self.command_ops.activate_device(user["id"], device["id"])
        container = self._create_container(user["id"], "workspace-11")

        first = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.CREATE, cpu=1, memory_bytes=1, storage_bytes=1,
        )
        self.assertTrue(first.success)
        self.command_ops.update({"id": first.data["id"]}, {"status": CommandStatus.SUCCEEDED})

        second = self.command_ops.reserve_quota_and_create_command(
            user_id=user["id"], device_id=device["id"], container_id=container["id"],
            operation=CommandOperation.RESUME, cpu=1, memory_bytes=1, storage_bytes=1,
        )
        self.assertTrue(second.success, f"A new command after the first completed should be allowed: {second.error}")
        print('OK')


class ZZZCleanup(TestCase):
    '''Cleanup the database after the tests.'''

    def test_cleanup(self) -> None:
        db_config = _db_config()
        migrator = Migrator(db_config, TEST_MIGRATIONS_DIR, versions_subdir="test_versions")
        migrator.reset_database()
        migrator.reset_migrations()
