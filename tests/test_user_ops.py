'''
Here in tests, we want to test the following:
1. Simple create user should work. We verify each field once the user is created.
2. Duplicate user creation should fail.
3. We need to check if changing emails within the same provider still points to the same user.
4. Different providers with same email should fail because email has a unique constraint in it.
5. last_login should be null by default and only have value when explicitly set.
6. is_active should be true by default and delete should set it to false without removing the user.
7. User should have 0 containers, orders and subscription at first.
8. When a user is deleted, all their containers, orders and subscription should be deleted (which would not happen because of soft delete, but we will test this anyways).
'''

# builtins
import os
from unittest import TestCase, mock
from datetime import datetime, timezone
import uuid

# third party
from dotenv import load_dotenv

# local
from src.operations.user_ops import UserOps
from src.operations.container_ops import ContainerOps
from src.operations.orders_ops import OrdersOps
from src.operations.subscription_ops import SubscriptionOps
from src.operations.subscription_type_ops import SubscriptionTypeOps
from src.operations import OperationResult
from src.common.config import DBConfig
from src.migrations.migrator import Migrator
from src.common.config import MIGRATIONS_DIR
from src.models.users import AuthProvider


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
        self.migrator: Migrator = Migrator(self.db_config, MIGRATIONS_DIR)

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


class TestUserOps(TestCase):
    '''
    All tests for UserOps
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.user_ops: UserOps = UserOps(self.db_config)
        self.container_ops: ContainerOps = ContainerOps(self.db_config)
        self.orders_ops: OrdersOps = OrdersOps(self.db_config)
        self.subscription_ops: SubscriptionOps = SubscriptionOps(self.db_config)
        self.subscription_type_ops: SubscriptionTypeOps = SubscriptionTypeOps(self.db_config)

    def test_1_simple_user_creation_with_field_verification(self) -> None:
        '''
        Test case 1: Simple create user should work. We verify each field once the user is created.
        '''
        print('test_1_simple_user_creation_with_field_verification: ', end="")
        # Create a user
        user_data: dict = {
            "email": "test@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_123",
            "is_active": True
        }
        result: OperationResult = self.user_ops.insert(user_data)

        # Verify the operation was successful
        self.assertTrue(result.success, f"User creation failed: {result.error}")
        self.assertEqual(result.message, "User created successfully")

        # Verify the returned data
        created_user: dict = result.data
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user["email"], user_data["email"])
        self.assertEqual(created_user["provider"], user_data["provider"].value)
        self.assertEqual(created_user["provider_id"], user_data["provider_id"])
        self.assertEqual(created_user["is_active"], user_data["is_active"])

        # Verify UUID is generated
        self.assertIsNotNone(created_user["id"])
        # Verify it's a valid UUID
        uuid.UUID(created_user["id"])

        # Verify timestamps are set
        self.assertIsNotNone(created_user["created_at"])
        self.assertIsNotNone(created_user["updated_at"])

        # Verify last_login is None by default
        self.assertIsNone(created_user["last_login"])

        # Verify we can find the user
        find_result = self.user_ops.find_one({"email": user_data["email"]})
        self.assertTrue(find_result.success)
        self.assertIsNotNone(find_result.data)
        self.assertEqual(find_result.data["id"], created_user["id"])

        # hard delete the user for test
        self.user_ops.delete({"id": created_user["id"]})
        print('OK')

    @mock.patch('src.operations.user_ops.logger.error', return_value='Duplicate user creation should fail. This is expected.')
    def test_2_duplicate_user_creation_should_fail(self, _: mock.MagicMock) -> None:
        '''
        Test case 2: Duplicate user creation should fail.
        NOTE: we are mocking the logger.error to avoid the error being logged to the console.
        '''
        print('test_2_duplicate_user_creation_should_fail: ', end="")
        user_data: dict = {
            "email": "duplicate@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_456",
            "is_active": True
        }
        # Create first user
        result1: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(result1.success, "First user creation should succeed")

        # Try to create duplicate user with same email
        result2: OperationResult = self.user_ops.insert(user_data)
        self.assertFalse(result2.success, "Duplicate user creation should fail")
        self.assertIn("already exists", result2.error.lower())

        # hard delete the user for test
        self.user_ops.delete({"email": user_data["email"]})
        print('OK')

    def test_3_email_change_same_provider_same_user(self) -> None:
        '''
        Test case 3: We need to check if changing emails within the same provider still points to the same user.
        Note: This test assumes we have logic to handle provider_id as the unique identifier.
        '''
        print('test_3_email_change_same_provider_same_user: ', end="")
        # Create user with initial email
        initial_data: dict = {
            "email": "initial@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_789",
            "is_active": True
        }
        result: OperationResult = self.user_ops.insert(initial_data)
        self.assertTrue(result.success)

        # Update email for the same provider_id
        update_result: OperationResult = self.user_ops.update(
            {"provider_id": "google_789", "provider": AuthProvider.GOOGLE},
            {"email": "updated@example.com"}
        )
        self.assertTrue(update_result.success)

        # Verify the user still exists with same ID but updated email
        find_result: OperationResult = self.user_ops.find_one({"provider_id": "google_789", "provider": AuthProvider.GOOGLE})
        self.assertTrue(find_result.success)
        self.assertEqual(find_result.data["email"], "updated@example.com")
        self.assertEqual(find_result.data["provider_id"], "google_789")

        # Verify old email doesn't exist
        old_email_result: OperationResult = self.user_ops.find_one({"email": "initial@example.com"})
        self.assertTrue(old_email_result.success)
        self.assertIsNone(old_email_result.data, "Old email should not be found")

        # hard delete the user for test
        self.user_ops.delete({"provider_id": "google_789", "provider": AuthProvider.GOOGLE})
        print('OK')

    def test_4_different_providers_same_email_different_accounts(self) -> None:
        '''
        Test case 4: Different providers with same email should fail because email has a unique constraint in it.
        '''
        print('test_4_different_providers_same_email_should_fail: ', end="")
        email: str = "shared@example.com"
        # Create Google user
        google_user: dict = {
            "email": email, 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_shared_123",
            "is_active": True
        }
        # Create GitHub user with same email
        github_user: dict = {
            "email": email, 
            "provider": AuthProvider.GITHUB, 
            "provider_id": "github_shared_456",
            "is_active": True
        }

        # Both should be created successfully
        google_result: OperationResult = self.user_ops.insert(google_user)
        self.assertTrue(google_result.success, "Google user creation should succeed")        
        github_result: OperationResult = self.user_ops.insert(github_user)
        self.assertFalse(github_result.success, "GitHub user creation should fail")
        self.assertIn("already exists", github_result.error.lower())

        # hard delete the users for test
        self.user_ops.delete({"provider_id": "google_shared_123", "provider": AuthProvider.GOOGLE})
        print('OK')

    def test_5_last_login_null_by_default_and_explicit_setting(self) -> None:
        '''
        Test case 5: last_login should be null by default and only have value when explicitly set.
        '''
        print('test_5_last_login_null_by_default_and_explicit_setting: ', end="")
        # Create user without last_login
        user_data: dict = {
            "email": "login_test@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_login_123",
            "is_active": True
        }

        result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(result.success)
        self.assertIsNone(result.data["last_login"], "last_login should be None by default")

        # Create user with explicit last_login
        login_time: str = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()  # isoformat without timezone
        user_with_login: dict = {
            "email": "login_test2@example.com", 
            "provider": AuthProvider.GITHUB, 
            "provider_id": "github_login_456",
            "is_active": True,
            "last_login": login_time
        }

        result2: OperationResult = self.user_ops.insert(user_with_login)
        self.assertTrue(result2.success)
        self.assertIsNotNone(result2.data["last_login"], "last_login should be set when provided")
        self.assertEqual(result2.data["last_login"], login_time)

        # Update last_login for first user
        new_login_time: str = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()  # isoformat without timezone
        update_result: OperationResult = self.user_ops.update(
            {"email": "login_test@example.com"},
            {"last_login": new_login_time}
        )
        self.assertTrue(update_result.success)

        # Verify the update
        find_result: OperationResult = self.user_ops.find_one({"email": "login_test@example.com"})
        self.assertTrue(find_result.success)
        self.assertEqual(find_result.data["last_login"], new_login_time)

        # hard delete the user for test
        self.user_ops.delete({"provider_id": "google_login_123", "provider": AuthProvider.GOOGLE})
        self.user_ops.delete({"provider_id": "github_login_456", "provider": AuthProvider.GITHUB})
        print('OK')

    def test_6_is_active_default_true_and_soft_delete(self) -> None:
        '''
        Test case 6: is_active should be true by default and deactivate should set it to false without removing the user.
                    Also, reactivate should set it to true.
        '''
        print('test_6_is_active_default_true_and_soft_delete: ', end="")
        # Create user (is_active should default to True)
        user_data: dict = {
            "email": "active_test@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_active_123"
            # Note: not setting is_active explicitly
        }

        result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(result.success)
        self.assertTrue(result.data["is_active"], "is_active should default to True")

        # Soft delete by setting is_active to False
        update_result: OperationResult = self.user_ops.deactivate(
            {"email": "active_test@example.com"}
        )
        self.assertTrue(update_result.success)

        # Verify user still exists but is inactive
        find_result: OperationResult = self.user_ops.find_one({"email": "active_test@example.com"})
        self.assertTrue(find_result.success)
        self.assertIsNotNone(find_result.data, "User should still exist after soft delete")
        self.assertFalse(find_result.data["is_active"], "User should be inactive after soft delete")

        # Reactivate user
        reactivate_result: OperationResult = self.user_ops.reactivate(
            {"email": "active_test@example.com"}
        )
        self.assertTrue(reactivate_result.success)

        # Verify user is active again
        find_result2: OperationResult = self.user_ops.find_one({"email": "active_test@example.com"})
        self.assertTrue(find_result2.success)
        self.assertTrue(find_result2.data["is_active"], "User should be active after reactivation")

        # hard delete the user for test
        self.user_ops.delete({"provider_id": "google_active_123", "provider": AuthProvider.GOOGLE})
        print('OK')

    def test_7_new_user_has_zero_related_records(self) -> None:
        '''
        Test case 7: User should have 0 containers, orders and subscription at first.
        '''
        print('test_7_new_user_has_zero_related_records: ', end="")
        # Create a user
        user_data: dict = {
            "email": "newuser@example.com", 
            "provider": AuthProvider.GOOGLE, 
            "provider_id": "google_newuser_123",
            "is_active": True
        }

        result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(result.success)
        user_id: str = result.data["id"]

        # Check containers
        containers_result: OperationResult = self.container_ops.find({"user_id": user_id})
        self.assertTrue(containers_result.success)
        self.assertEqual(len(containers_result.data), 0, "New user should have 0 containers")

        # Check orders
        orders_result: OperationResult = self.orders_ops.find({"user_id": user_id})
        self.assertTrue(orders_result.success)
        self.assertEqual(len(orders_result.data), 0, "New user should have 0 orders")

        # Check subscription
        subscription_result: OperationResult = self.subscription_ops.find({"user_id": user_id})
        self.assertTrue(subscription_result.success)
        self.assertEqual(len(subscription_result.data), 0, "New user should have 0 subscriptions")

        # hard delete the user for test
        self.user_ops.delete({"provider_id": "google_newuser_123", "provider": AuthProvider.GOOGLE})
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
        self.migrator: Migrator = Migrator(self.db_config, MIGRATIONS_DIR)

    def test_cleanup(self) -> None:
        self.migrator.reset_database()
        self.migrator.reset_migrations()
