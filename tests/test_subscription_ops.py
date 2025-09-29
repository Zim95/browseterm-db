'''
Here in tests, we want to test the following:
1. Simple create subscription with valid user and subscription type should work. We verify each field once the subscription is created.
2. Create subscription with invalid user should fail.
3. Create subscription with invalid subscription type should fail.
4. Duplicate subscription creation should fail (user can only have one subscription).
5. Subscription with invalid status should fail.
6. Soft delete subscription should work (status=CANCELLED, cancelled_at set).
7. Hard delete subscription should work and delete related orders.
8. Create subscription with minimal data should use default values.
'''

# builtins
from dotenv import load_dotenv
from unittest import TestCase
import os
from datetime import datetime, timezone

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import MIGRATIONS_DIR
from browseterm_db.operations.subscription_ops import SubscriptionOps
from browseterm_db.operations.user_ops import UserOps
from browseterm_db.operations.subscription_type_ops import SubscriptionTypeOps
from browseterm_db.operations.orders_ops import OrdersOps
from browseterm_db.models.users import AuthProvider
from browseterm_db.models.subscriptions import SubscriptionStatus
from browseterm_db.models.subscription_types import SubscriptionTypeCurrency
from browseterm_db.models.orders import OrdersCurrency, OrderStatus
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

class TestSubscriptionOps(TestCase):
    '''
    Test the subscription operations
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.subscription_ops: SubscriptionOps = SubscriptionOps(self.db_config)
        self.user_ops: UserOps = UserOps(self.db_config)
        self.subscription_type_ops: SubscriptionTypeOps = SubscriptionTypeOps(self.db_config)
        self.orders_ops: OrdersOps = OrdersOps(self.db_config)

    def test_1_simple_subscription_creation_with_field_verification(self) -> None:
        '''
        Test case 1: Simple create subscription with valid user and subscription type should work. We verify each field once the subscription is created.
        '''
        print('test_1_simple_subscription_creation_with_field_verification: ', end="")
        # Create a user
        user_data: dict = {
            "email": "subscription_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_123",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Basic subscription plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create a subscription
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "status": SubscriptionStatus.ACTIVE,
            "auto_renew": True,
            "valid_until": "2025-12-31T23:59:59"
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "Subscription creation should succeed")
        # Verify all fields
        self.assertEqual(subscription_result.data["user_id"], user_id)
        self.assertEqual(subscription_result.data["subscription_type_id"], subscription_type_id)
        self.assertEqual(subscription_result.data["status"], subscription_data["status"].value)
        self.assertEqual(subscription_result.data["auto_renew"], subscription_data["auto_renew"])
        self.assertEqual(subscription_result.data["valid_until"], subscription_data["valid_until"])
        self.assertEqual(subscription_result.data["created_at"] is not None, True)
        self.assertEqual(subscription_result.data["updated_at"] is not None, True)
        self.assertEqual(subscription_result.data["cancelled_at"], None)
        # Cleanup
        self.subscription_ops.delete({"id": subscription_result.data["id"]})
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_2_subscription_creation_with_invalid_user_should_fail(self) -> None:
        '''
        Test case 2: Create subscription with invalid user should fail.
        '''
        print('test_2_subscription_creation_with_invalid_user_should_fail: ', end="")
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Basic subscription plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create a subscription with invalid user
        subscription_data: dict = {
            "user_id": "invalid_user_id",
            "subscription_type_id": subscription_type_id,
            "status": SubscriptionStatus.ACTIVE,
            "auto_renew": True,
            "valid_until": "2025-12-31T23:59:59"
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertFalse(subscription_result.success, "Subscription creation should fail")
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        print('OK')

    def test_3_subscription_creation_with_invalid_subscription_type_should_fail(self) -> None:
        '''
        Test case 3: Create subscription with invalid subscription type should fail.
        '''
        print('test_3_subscription_creation_with_invalid_subscription_type_should_fail: ', end="")
        # Create a user
        user_data: dict = {
            "email": "subscription_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_123",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription with invalid subscription type
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": "invalid_subscription_type_id",
            "status": SubscriptionStatus.ACTIVE,
            "auto_renew": True,
            "valid_until": "2025-12-31T23:59:59"
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertFalse(subscription_result.success, "Subscription creation should fail")
        # Cleanup
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_4_duplicate_subscription_creation_should_fail(self) -> None:
        '''
        Test case 4: Duplicate subscription creation should fail (user can only have one subscription).
        '''
        print('test_4_duplicate_subscription_creation_should_fail: ', end="")
        # Create a user
        user_data: dict = {
            "email": "subscription_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_123",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Basic subscription plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create first subscription
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "status": SubscriptionStatus.ACTIVE,
            "auto_renew": True,
            "valid_until": "2025-12-31T23:59:59"
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "First subscription creation should succeed")
        # Try to create duplicate subscription for same user
        duplicate_subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertFalse(duplicate_subscription_result.success, "Duplicate subscription creation should fail")
        # Cleanup
        self.subscription_ops.delete({"id": subscription_result.data["id"]})
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_5_subscription_creation_with_invalid_status_should_fail(self) -> None:
        '''
        Test case 5: Subscription with invalid status should fail.
        '''
        print('test_5_subscription_creation_with_invalid_status_should_fail: ', end="")
        # Create a user
        user_data: dict = {
            "email": "subscription_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_123",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Basic subscription plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create subscription with invalid status
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "status": "INVALID_STATUS",
            "auto_renew": True,
            "valid_until": "2025-12-31T23:59:59"
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertFalse(subscription_result.success, "Subscription creation should fail")
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_6_subscription_soft_delete_should_work(self) -> None:
        '''
        Test case 6: Soft delete subscription should work (status=CANCELLED, cancelled_at set).
        '''
        print('test_6_subscription_soft_delete_should_work: ', end="")
        # Create a user
        user_data: dict = {
            "email": "subscription_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_123",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Basic subscription plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create a subscription
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "status": SubscriptionStatus.ACTIVE,
            "auto_renew": True,
            "valid_until": "2025-12-31T23:59:59"
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "Subscription creation should succeed")
        subscription_id: str = subscription_result.data["id"]
        # Soft delete the subscription
        soft_delete_result: OperationResult = self.subscription_ops.soft_delete({"id": subscription_id})
        self.assertTrue(soft_delete_result.success, "Subscription soft delete should succeed")
        # Verify subscription is soft deleted (status=CANCELLED, cancelled_at set)
        find_result: OperationResult = self.subscription_ops.find_one({"id": subscription_id})
        self.assertTrue(find_result.success, "Subscription should still exist")
        self.assertEqual(find_result.data["status"], SubscriptionStatus.CANCELLED.value)
        self.assertIsNotNone(find_result.data["cancelled_at"])
        # Cleanup
        self.subscription_ops.delete({"id": subscription_id})
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_7_subscription_hard_delete_should_delete_related_orders(self) -> None:
        '''
        Test case 7: Hard delete subscription should work and delete related orders.
        '''
        print('test_7_subscription_hard_delete_should_delete_related_orders: ', end="")
        # Create a user
        user_data: dict = {
            "email": "subscription_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_123",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Basic subscription plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create a subscription
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "status": SubscriptionStatus.ACTIVE,
            "auto_renew": True,
            "valid_until": "2025-12-31T23:59:59"
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "Subscription creation should succeed")
        subscription_id: str = subscription_result.data["id"]
        # Create an order for this subscription
        order_data: dict = {
            "user_id": user_id,
            "subscription_id": subscription_id,
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": OrdersCurrency.INR,
            "status": OrderStatus.PAID,
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertTrue(order_result.success, "Order creation should succeed")
        order_id: str = order_result.data["id"]
        # Hard delete the subscription
        delete_result: OperationResult = self.subscription_ops.delete({"id": subscription_id})
        self.assertTrue(delete_result.success, "Subscription hard delete should succeed")
        # Verify subscription is deleted
        subscription_find_result: OperationResult = self.subscription_ops.find_one({"id": subscription_id})
        self.assertTrue(subscription_find_result.success, "Subscription should be deleted")
        self.assertEqual(subscription_find_result.data, None)
        # Verify related order is also deleted due to CASCADE
        order_find_result: OperationResult = self.orders_ops.find_one({"id": order_id})
        self.assertTrue(order_find_result.success, "Order should be deleted due to CASCADE")
        self.assertEqual(order_find_result.data, None)
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_8_subscription_creation_with_default_values(self) -> None:
        '''
        Test case 8: Create subscription with minimal data should use default values.
        '''
        print('test_8_subscription_creation_with_default_values: ', end="")
        # Create a user
        user_data: dict = {
            "email": "subscription_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_123",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Basic subscription plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create subscription with minimal data
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "Subscription creation should succeed")
        # Verify default values are applied
        self.assertEqual(subscription_result.data["status"], SubscriptionStatus.PENDING.value)  # default status
        self.assertEqual(subscription_result.data["auto_renew"], True)  # default auto_renew
        self.assertIsNotNone(subscription_result.data["valid_until"])  # calculated valid_until
        self.assertIsNone(subscription_result.data["cancelled_at"])  # nullable field
        # Cleanup
        self.subscription_ops.delete({"id": subscription_result.data["id"]})
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
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
