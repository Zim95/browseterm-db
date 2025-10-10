'''
Here, we need to test the following:
1. Create order with valid data should work. Validate each field. Subscription ID should be None at the start.
2. Create order with invalid user should fail.
3. Create order with invalid order status should fail.
4. Create order with invalid currency should fail.
5. Deleting order should not delete the user.
6. Deleting order should not delete the subscription.
7. Deleting order should not delete the subscription type.
'''

from dotenv import load_dotenv
from unittest import TestCase
import os

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import MIGRATIONS_DIR
from browseterm_db.models.subscriptions import SubscriptionStatus
from browseterm_db.operations.orders_ops import OrdersOps
from browseterm_db.operations.user_ops import UserOps
from browseterm_db.operations.subscription_type_ops import SubscriptionTypeOps
from browseterm_db.operations.subscription_ops import SubscriptionOps
from browseterm_db.models.users import AuthProvider
from browseterm_db.models.orders import OrderStatus, OrdersCurrency
from browseterm_db.models.subscription_types import SubscriptionTypeCurrency
from browseterm_db.operations import OperationResult
from browseterm_db.models.containers import DEFAULT_CPU_LIMIT, DEFAULT_MEMORY_LIMIT


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


class TestOrderOps(TestCase):
    '''
    Test the order operations
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.orders_ops: OrdersOps = OrdersOps(self.db_config)
        self.user_ops: UserOps = UserOps(self.db_config)
        self.subscription_type_ops: SubscriptionTypeOps = SubscriptionTypeOps(self.db_config)
        self.subscription_ops: SubscriptionOps = SubscriptionOps(self.db_config)

    def test_1_create_order_with_valid_data_should_work(self) -> None:
        '''
        Test case 1: Create order with valid data should work. Validate each field. Subscription ID should be None at the start.
        '''
        print('test_1_create_order_with_valid_data_should_work: ', end="")
        # Create a user
        user_data: dict = {
            "email": "order_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_order_123",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
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
            "max_containers": 1,
            "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
            "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
            "description": "Basic subscription plan for testing",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create an order
        order_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": OrdersCurrency.INR,
            "status": OrderStatus.PENDING,
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertTrue(order_result.success, "Order creation should succeed")
        # Verify the order fields
        self.assertEqual(order_result.data["user_id"], user_id)
        self.assertEqual(order_result.data["subscription_type_id"], subscription_type_id)
        self.assertEqual(order_result.data["subscription_id"], None)  # Should be None initially
        self.assertEqual(order_result.data["amount"], 999.0)
        self.assertEqual(order_result.data["currency"], OrdersCurrency.INR.value)
        self.assertEqual(order_result.data["status"], OrderStatus.PENDING.value)
        self.assertEqual(order_result.data["payment_method"], "stripe")
        self.assertEqual(order_result.data["paid_at"], None)  # Should be None for pending order
        self.assertEqual(order_result.data["created_at"] is not None, True)
        self.assertEqual(order_result.data["updated_at"] is not None, True)
        # Cleanup
        self.orders_ops.delete({"id": order_result.data["id"]})
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_2_create_order_with_invalid_user_should_fail(self) -> None:
        '''
        Test case 2: Create order with invalid user should fail.
        '''
        print('test_2_create_order_with_invalid_user_should_fail: ', end="")
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Basic Plan",
            "type": "basic",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 1,
            "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
            "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
            "description": "Basic subscription plan for testing",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create an order with invalid user
        order_data: dict = {
            "user_id": "invalid_user_id",
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": OrdersCurrency.INR,
            "status": OrderStatus.PENDING,
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertFalse(order_result.success, "Order creation should fail with invalid user")
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        print('OK')

    def test_3_create_order_with_invalid_order_status_should_fail(self) -> None:
        '''
        Test case 3: Create order with invalid order status should fail.
        '''
        print('test_3_create_order_with_invalid_order_status_should_fail: ', end="")
        # Create a user
        user_data: dict = {
            "email": "invalid_status@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_invalid_status_123",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
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
            "max_containers": 1,
            "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
            "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
            "description": "Basic subscription plan for testing",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create an order with invalid status
        order_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": OrdersCurrency.INR,
            "status": "INVALID_STATUS",
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertFalse(order_result.success, "Order creation should fail with invalid status")
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_4_create_order_with_invalid_currency_should_fail(self) -> None:
        '''
        Test case 4: Create order with invalid currency should fail.
        '''
        print('test_4_create_order_with_invalid_currency_should_fail: ', end="")
        # Create a user
        user_data: dict = {
            "email": "invalid_currency@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_invalid_currency_123",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
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
            "max_containers": 1,
            "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
            "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
            "description": "Basic subscription plan for testing",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create an order with invalid currency
        order_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": "INVALID_CURRENCY",
            "status": OrderStatus.PENDING,
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertFalse(order_result.success, "Order creation should fail with invalid currency")
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_5_deleting_order_should_not_delete_user(self) -> None:
        '''
        Test case 5: Deleting order should not delete the user.
        '''
        print('test_5_deleting_order_should_not_delete_user: ', end="")
        # Create a user
        user_data: dict = {
            "email": "delete_order@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_delete_order_123",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
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
            "max_containers": 1,
            "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
            "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
            "description": "Basic subscription plan for testing",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create an order
        order_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": OrdersCurrency.INR,
            "status": OrderStatus.PENDING,
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertTrue(order_result.success, "Order creation should succeed")
        order_id: str = order_result.data["id"]
        # Delete the order
        delete_result: OperationResult = self.orders_ops.delete({"id": order_id})
        self.assertTrue(delete_result.success, "Order deletion should succeed")
        # Verify order is deleted
        order_find_result: OperationResult = self.orders_ops.find_one({"id": order_id})
        self.assertTrue(order_find_result.success, "Order should be deleted")
        self.assertEqual(order_find_result.data, None)
        # Verify user still exists
        user_find_result: OperationResult = self.user_ops.find_one({"id": user_id})
        self.assertTrue(user_find_result.success, "User should still exist")
        self.assertEqual(user_find_result.data["is_active"], True)
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_6_deleting_order_should_not_delete_subscription(self) -> None:
        '''
        Test case 6: Deleting order should not delete the subscription.
        '''
        print('test_6_deleting_order_should_not_delete_subscription: ', end="")
        # Create a user
        user_data: dict = {
            "email": "order_subscription@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_order_sub_123",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
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
            "max_containers": 1,
            "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
            "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
            "description": "Basic subscription plan for testing",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create a subscription
        subscription_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "valid_until": "2025-12-31T23:59:59",
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "Subscription creation should succeed")
        subscription_id: str = subscription_result.data["id"]
        # Create an order linked to the subscription
        order_data: dict = {
            "user_id": user_id,
            "subscription_id": subscription_id,
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": OrdersCurrency.INR,
            "status": OrderStatus.PENDING,
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertTrue(order_result.success, "Order creation should succeed")
        order_id: str = order_result.data["id"]
        # Delete the order
        delete_result: OperationResult = self.orders_ops.delete({"id": order_id})
        self.assertTrue(delete_result.success, "Order deletion should succeed")
        # Verify order is deleted
        order_find_result: OperationResult = self.orders_ops.find_one({"id": order_id})
        self.assertTrue(order_find_result.success, "Order should be deleted")
        self.assertEqual(order_find_result.data, None)
        # Verify subscription still exists
        subscription_find_result: OperationResult = self.subscription_ops.find_one({"id": subscription_id})
        self.assertTrue(subscription_find_result.success, "Subscription should still exist")
        self.assertEqual(subscription_find_result.data["status"], SubscriptionStatus.PENDING.value)
        # Cleanup
        self.subscription_ops.delete({"id": subscription_id})
        self.subscription_type_ops.delete({"id": subscription_type_id})
        self.user_ops.delete({"id": user_id})
        print('OK')

    def test_7_deleting_order_should_not_delete_subscription_type(self) -> None:
        '''
        Test case 7: Deleting order should not delete the subscription type.
        '''
        print('test_7_deleting_order_should_not_delete_subscription_type: ', end="")
        # Create a user
        user_data: dict = {
            "email": "order_sub_type@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_order_sub_type_123",
            "name": "Test User",
            "profile_picture_url": "https://example.com/profile.jpg",
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
            "max_containers": 1,
            "cpu_limit_per_container": DEFAULT_CPU_LIMIT,
            "memory_limit_per_container": DEFAULT_MEMORY_LIMIT,
            "description": "Basic subscription plan for testing",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Create an order
        order_data: dict = {
            "user_id": user_id,
            "subscription_type_id": subscription_type_id,
            "amount": 999,
            "currency": OrdersCurrency.INR,
            "status": OrderStatus.PENDING,
            "payment_method": "stripe"
        }
        order_result: OperationResult = self.orders_ops.insert(order_data)
        self.assertTrue(order_result.success, "Order creation should succeed")
        order_id: str = order_result.data["id"]
        # Delete the order
        delete_result: OperationResult = self.orders_ops.delete({"id": order_id})
        self.assertTrue(delete_result.success, "Order deletion should succeed")
        # Verify order is deleted
        order_find_result: OperationResult = self.orders_ops.find_one({"id": order_id})
        self.assertTrue(order_find_result.success, "Order should be deleted")
        self.assertEqual(order_find_result.data, None)
        # Verify subscription type still exists
        sub_type_find_result: OperationResult = self.subscription_type_ops.find_one({"id": subscription_type_id})
        self.assertTrue(sub_type_find_result.success, "Subscription type should still exist")
        self.assertEqual(sub_type_find_result.data["is_active"], True)
        # Cleanup
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
