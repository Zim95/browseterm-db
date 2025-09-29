'''
Here, we need to test the following:
1. Creating a subscription type should work. We also validate each field.
2. Create a subscription, user and order based on subscription type. Deleting the subscription type should not delete anything else.
3. Duplicate subscription type creation should fail.
4. Create subscription type with invalid currency should fail.
5. Soft delete subscription type should work.
6. Create subscription type with minimal data should use default values.
7. Deleting subscription type should delete all related subscriptions and orders - This is tested in test_2_deleting_subscription_type_should_not_delete_related_data.
8. Hard delete should delete all the associated rows in relationships.
'''

# builtins
from dotenv import load_dotenv
from unittest import TestCase
import os
from typing import List, Dict, Any

# local
from src.common.config import DBConfig
from src.migrations.migrator import Migrator
from src.common.config import MIGRATIONS_DIR
from src.operations.subscription_type_ops import SubscriptionTypeOps
from src.operations.user_ops import UserOps
from src.operations.subscription_ops import SubscriptionOps
from src.operations.orders_ops import OrdersOps
from src.models.users import AuthProvider
from src.models.subscription_types import SubscriptionTypeCurrency
from src.models.orders import OrderStatus, OrdersCurrency
from src.operations import OperationResult


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


class TestSubscriptionTypeOps(TestCase):
    '''
    Test the subscription type operations
    '''
    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )
        self.subscription_type_ops: SubscriptionTypeOps = SubscriptionTypeOps(self.db_config)
        self.user_ops: UserOps = UserOps(self.db_config)
        self.subscription_ops: SubscriptionOps = SubscriptionOps(self.db_config)
        self.orders_ops: OrdersOps = OrdersOps(self.db_config)
        # self.default_subscription_types: List[Dict[str, Any]] = [
        #     {
        #         "name": "Free Plan",
        #         "type": "free",
        #         "amount": 0,
        #         "currency": Currency.INR,
        #         "duration_days": 365,  # 1 year
        #         "max_containers": 1,
        #         "cpu_limit_per_container": "1",
        #         "memory_limit_per_container": "1GB",
        #         "description": "Free plan with basic container limits",
        #         "is_active": True
        #     },
        #     {
        #         "name": "Basic Plan",
        #         "type": "basic",
        #         "amount": 100,
        #         "currency": Currency.INR,
        #         "duration_days": 30,  # 1 month
        #         "max_containers": 5,
        #         "cpu_limit_per_container": "1",
        #         "memory_limit_per_container": "1GB",x
        #         "description": "Basic plan with increased container limits",
        #         "is_active": True
        #     }
        # ]
        # self.subscription_type_ops.insert_many(self.default_subscription_types)

    def test_1_subscription_type_creation_with_field_validation(self) -> None:
        '''
        Test case 1: Creating a subscription type should work. We also validate each field.
        '''
        print('test_1_subscription_type_creation_with_field_validation: ', end="")
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Premium Plan",
            "type": "premium",
            "amount": 1999,
            "currency": SubscriptionTypeCurrency.INR.value,
            "duration_days": 30,
            "max_containers": 5,
            "cpu_limit_per_container": "2",
            "memory_limit_per_container": "4GB",
            "description": "Premium subscription plan with enhanced features",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        # Verify all fields
        self.assertEqual(sub_type_result.data["name"], subscription_type_data["name"])
        self.assertEqual(sub_type_result.data["type"], subscription_type_data["type"])
        self.assertEqual(sub_type_result.data["amount"], float(subscription_type_data["amount"]))
        self.assertEqual(sub_type_result.data["currency"], subscription_type_data["currency"])
        self.assertEqual(sub_type_result.data["duration_days"], subscription_type_data["duration_days"])
        self.assertEqual(sub_type_result.data["max_containers"], subscription_type_data["max_containers"])
        self.assertEqual(sub_type_result.data["cpu_limit_per_container"], subscription_type_data["cpu_limit_per_container"])
        self.assertEqual(sub_type_result.data["memory_limit_per_container"], subscription_type_data["memory_limit_per_container"])
        self.assertEqual(sub_type_result.data["description"], subscription_type_data["description"])
        self.assertEqual(sub_type_result.data["is_active"], subscription_type_data["is_active"])
        self.assertEqual(sub_type_result.data["created_at"] is not None, True)
        self.assertEqual(sub_type_result.data["updated_at"] is not None, True)
        # Cleanup
        self.subscription_type_ops.delete({"id": sub_type_result.data["id"]})
        print('OK')

    def test_2_deleting_subscription_type_should_not_delete_related_data(self) -> None:
        '''
        Test case 2: Create a subscription, user and order based on subscription type. Deleting the subscription type should not delete anything else.
        '''
        print('test_2_deleting_subscription_type_should_not_delete_related_data: ', end="")
        # Create a user
        user_data: dict = {
            "email": "sub_type_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_type_test_1",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Test Plan",
            "type": "test_plan",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Test subscription plan",
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
            "is_active": True
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "Subscription creation should succeed")
        subscription_id: str = subscription_result.data["id"]
        # Create an order
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
        # Soft delete the subscription type
        delete_sub_type_result: OperationResult = self.subscription_type_ops.soft_delete({"id": subscription_type_id})
        self.assertTrue(delete_sub_type_result.success, "Subscription type soft deletion should succeed")
        # Verify subscription type is soft deleted (is_active=False)
        sub_type_find_result: OperationResult = self.subscription_type_ops.find_one({"id": subscription_type_id})
        self.assertTrue(sub_type_find_result.success, "Subscription type should still exist")
        self.assertEqual(sub_type_find_result.data["is_active"], False)
        # Verify user still exists
        user_find_result: OperationResult = self.user_ops.find_one({"id": user_id})
        self.assertTrue(user_find_result.success, "User should still exist")
        self.assertEqual(user_find_result.data["is_active"], True)
        # Verify subscription still exists
        subscription_find_result: OperationResult = self.subscription_ops.find_one({"id": subscription_id})
        self.assertTrue(subscription_find_result.success, "Subscription should still exist")
        self.assertEqual(subscription_find_result.data["subscription_type_id"], subscription_type_id)
        # Verify order still exists
        order_find_result: OperationResult = self.orders_ops.find_one({"id": order_id})
        self.assertTrue(order_find_result.success, "Order should still exist")
        self.assertEqual(order_find_result.data["subscription_type_id"], subscription_type_id)
        # Cleanup
        self.orders_ops.delete({"id": order_id})
        self.subscription_ops.delete({"id": subscription_id})
        self.user_ops.delete({"id": user_id})
        self.subscription_type_ops.delete({"id": subscription_type_id})
        print('OK')

    def test_3_duplicate_subscription_type_creation_should_fail(self) -> None:
        '''
        Test case 3: Duplicate subscription type creation should fail.
        '''
        print('test_3_duplicate_subscription_type_creation_should_fail: ', end="")
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Duplicate Plan",
            "type": "duplicate_plan",
            "amount": 1499,
            "currency": SubscriptionTypeCurrency.INR.value,
            "duration_days": 30,
            "max_containers": 3,
            "cpu_limit_per_container": "1.5",
            "memory_limit_per_container": "3GB",
            "description": "Duplicate test plan",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "First subscription type creation should succeed")
        # Try to create duplicate subscription type (same type field)
        duplicate_sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertFalse(duplicate_sub_type_result.success, "Duplicate subscription type creation should fail")
        # Cleanup
        self.subscription_type_ops.delete({"id": sub_type_result.data["id"]})
        print('OK')

    def test_4_subscription_type_creation_with_invalid_currency_should_fail(self) -> None:
        '''
        Test case 4: Create subscription type with invalid currency should fail.
        '''
        print('test_4_subscription_type_creation_with_invalid_currency_should_fail: ', end="")
        # Create subscription type with invalid currency
        subscription_type_data: dict = {
            "name": "Invalid Currency Plan",
            "type": "invalid_currency_plan",
            "amount": 999,
            "currency": "INVALID_CURRENCY",
            "duration_days": 30,
            "max_containers": 1,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "1GB",
            "description": "Plan with invalid currency",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertFalse(sub_type_result.success, "Subscription type creation with invalid currency should fail")
        print('OK')

    def test_5_subscription_type_soft_delete_with_is_active_false(self) -> None:
        '''
        Test case 5: Setting is_active to False should soft delete the subscription type.
        '''
        print('test_5_subscription_type_soft_delete_with_is_active_false: ', end="")
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Soft Delete Plan",
            "type": "soft_delete_plan",
            "amount": 799,
            "currency": SubscriptionTypeCurrency.INR.value,
            "duration_days": 30,
            "max_containers": 1,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "1GB",
            "description": "Plan for soft delete test",
            "is_active": True
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        subscription_type_id: str = sub_type_result.data["id"]
        # Update to set is_active = False (soft delete)
        update_data: dict = {"is_active": False}
        update_result: OperationResult = self.subscription_type_ops.update({"id": subscription_type_id}, update_data)
        self.assertTrue(update_result.success, "Subscription type update should succeed")
        # Verify the subscription type still exists but is inactive
        find_result: OperationResult = self.subscription_type_ops.find_one({"id": subscription_type_id})
        self.assertTrue(find_result.success, "Subscription type should still exist")
        self.assertEqual(find_result.data["is_active"], False)
        # Cleanup
        self.subscription_type_ops.delete({"id": subscription_type_id})
        print('OK')

    def test_6_subscription_type_creation_with_default_values(self) -> None:
        '''
        Test case 6: Create subscription type with minimal data should use default values.
        '''
        print('test_6_subscription_type_creation_with_default_values: ', end="")
        # Create subscription type with minimal required fields
        subscription_type_data: dict = {
            "name": "Minimal Plan",
            "type": "minimal_plan",
            "amount": 499,
            "duration_days": 30
        }
        sub_type_result: OperationResult = self.subscription_type_ops.insert(subscription_type_data)
        self.assertTrue(sub_type_result.success, "Subscription type creation should succeed")
        # Verify default values are applied
        self.assertEqual(sub_type_result.data["currency"], SubscriptionTypeCurrency.INR.value)  # default currency
        self.assertEqual(sub_type_result.data["max_containers"], 1)  # default max_containers
        self.assertEqual(sub_type_result.data["cpu_limit_per_container"], "1")  # default cpu_limit
        self.assertEqual(sub_type_result.data["memory_limit_per_container"], "1GB")  # default memory_limit
        self.assertEqual(sub_type_result.data["is_active"], True)  # default is_active
        self.assertEqual(sub_type_result.data["description"], None)  # nullable field
        # Cleanup
        self.subscription_type_ops.delete({"id": sub_type_result.data["id"]})
        print('OK')

    def test_7_hard_delete_subscription_type(self) -> None:
        '''
        Hard deleting subscription type should delete all associated subscriptions and orders.
        '''
        print('test_7_hard_delete_subscription_type: ', end="")
        # Create a user
        user_data: dict = {
            "email": "sub_type_test@example.com",
            "provider": AuthProvider.GOOGLE,
            "provider_id": "google_sub_type_test_1",
            "is_active": True
        }
        user_result: OperationResult = self.user_ops.insert(user_data)
        self.assertTrue(user_result.success, "User creation should succeed")
        user_id: str = user_result.data["id"]
        # Create a subscription type
        subscription_type_data: dict = {
            "name": "Test Plan",
            "type": "test_plan",
            "amount": 999,
            "currency": SubscriptionTypeCurrency.INR,
            "duration_days": 30,
            "max_containers": 2,
            "cpu_limit_per_container": "1",
            "memory_limit_per_container": "2GB",
            "description": "Test subscription plan",
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
            "is_active": True
        }
        subscription_result: OperationResult = self.subscription_ops.insert(subscription_data)
        self.assertTrue(subscription_result.success, "Subscription creation should succeed")
        subscription_id: str = subscription_result.data["id"]
        # Create an order
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
        # Soft delete the subscription type
        delete_sub_type_result: OperationResult = self.subscription_type_ops.delete({"id": subscription_type_id})
        self.assertTrue(delete_sub_type_result.success, "Subscription type soft deletion should succeed")
        # Verify subscription type is hard deleted
        sub_type_find_result: OperationResult = self.subscription_type_ops.find_one({"id": subscription_type_id})
        self.assertTrue(sub_type_find_result.success, "Subscription type should be deleted")
        self.assertEqual(sub_type_find_result.data, None)
        # Verify user still exists
        user_find_result: OperationResult = self.user_ops.find_one({"id": user_id})
        self.assertTrue(user_find_result.success, "User should still exist")
        self.assertEqual(user_find_result.data["is_active"], True)
        # Verify subscription still exists
        subscription_find_result: OperationResult = self.subscription_ops.find_one({"id": subscription_id})
        self.assertTrue(subscription_find_result.success, "Subscription should be deleted")
        self.assertEqual(subscription_find_result.data, None)
        # Verify order still exists
        order_find_result: OperationResult = self.orders_ops.find_one({"id": order_id})
        self.assertTrue(order_find_result.success, "Order should be deleted")
        self.assertEqual(order_find_result.data, None)
        # Cleanup
        self.user_ops.delete({"id": user_id})
        self.subscription_type_ops.delete({"id": subscription_type_id})
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
