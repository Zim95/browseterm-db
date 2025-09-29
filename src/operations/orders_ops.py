"""
Orders operations - Database operations for Orders model

NOTE:

What is synchronize_session?
----------------------------
- synchronize_session is a flag that indicates whether to synchronize the session after the update.
- If True, the session will be synchronized after the update.
- If False, the session will not be synchronized after the update.
- If None, the session will be synchronized after the update if the session is dirty.
- If the session is not dirty, the session will not be synchronized after the update.
- If the session is dirty, the session will be synchronized after the update.

Why do we set synchronize_session to False?
-------------------------------------------
- synchronize_session is set to False to avoid the session being synchronized after the update.
- This is because we are updating the session manually.
- If we set synchronize_session to True, the session will be synchronized after the update and the session will be updated with the new values.
- This is not what we want.
- We explicitly control transaction commits rather than using auto-commit, allowing us to handle commit failures and return appropriate error responses.
"""

# builtins
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from decimal import Decimal
import logging

# sqlalchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, Query

# local
from src.models.orders import Orders, OrderStatus, OrdersCurrency
from src.operations import DBOperations, OperationResult


logger = logging.getLogger(__name__)


class OrdersOps(DBOperations):
    """
    Orders operations implementing DBOperations abstract class
    """

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'subscription_type_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'subscription_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update values to appropriate types"""
        update_conversion_map: dict = {
            'currency': lambda value: value.value if isinstance(value, OrdersCurrency) else value,
            'status': lambda value: value.value if isinstance(value, OrderStatus) else value,
            'paid_at': lambda value: datetime.fromisoformat(value) if isinstance(value, str) else value,
            'subscription_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'subscription_type_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'amount': lambda value: Decimal(str(value)) if value is not None else None,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None, 
             offset: Optional[int] = None) -> OperationResult:
        """Find multiple orders based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Orders)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Orders, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Orders, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            orders: List[Orders] = query.all()
            result_list: List[Dict[str, Any]] = [order.to_dict() for order in orders]
            self._close_session()
            return OperationResult(
                success=True, 
                message=f"Found {len(result_list)} orders", 
                data=result_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        """Find a single order based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Orders)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Orders, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Orders, key) == converted_value)
            order: Orders = query.first()
            result_data: Dict[str, Any] | None = None
            message: str = "Order not found"
            if order:
                result_data: Dict[str, Any] = order.to_dict()
                message: str = "Order found"
            self._close_session()
            return OperationResult(
                success=True, 
                message=message, 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error finding order: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding order: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single order"""
        try:
            session: Session = self._get_session()
            # Convert UUIDs if they're strings
            user_id: uuid.UUID = uuid.UUID(data.get('user_id')) if isinstance(data.get('user_id'), str) else data.get('user_id')
            subscription_id: uuid.UUID = uuid.UUID(data.get('subscription_id')) if isinstance(data.get('subscription_id'), str) else data.get('subscription_id')
            subscription_type_id: uuid.UUID = uuid.UUID(data.get('subscription_type_id')) if isinstance(data.get('subscription_type_id'), str) else data.get('subscription_type_id')
            amount: Decimal = Decimal(str(data.get('amount', 0)))
            currency: OrdersCurrency = OrdersCurrency(data.get('currency')) if isinstance(data.get('currency'), str) else data.get('currency', OrdersCurrency.INR)
            status: OrderStatus = OrderStatus(data.get('status')) if isinstance(data.get('status'), str) else data.get('status', OrderStatus.PENDING)
            payment_method: str = data.get('payment_method')
            payment_provider_id: str = data.get('payment_provider_id')
            paid_at: datetime = datetime.fromisoformat(data['paid_at']) if data.get('paid_at') else None if isinstance(data.get('paid_at'), str) else data.get('paid_at')
            # Create order instance
            order: Orders = Orders(
                user_id=user_id,
                subscription_id=subscription_id,
                subscription_type_id=subscription_type_id,
                amount=amount,
                currency=currency,
                status=status,
                payment_method=payment_method,
                payment_provider_id=payment_provider_id,
                paid_at=paid_at
            )
            session.add(order)
            session.flush()  # Get the ID without committing
            result_data: Dict[str, Any] = order.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message="Order created successfully", 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating order: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating order: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error creating order: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple orders"""
        try:
            session: Session = self._get_session()
            orders: List[Orders] = []
            for data in data_list:
                user_id: uuid.UUID = uuid.UUID(data.get('user_id')) if isinstance(data.get('user_id'), str) else data.get('user_id')
                subscription_id: uuid.UUID = uuid.UUID(data.get('subscription_id')) if isinstance(data.get('subscription_id'), str) else data.get('subscription_id')
                subscription_type_id: uuid.UUID = uuid.UUID(data.get('subscription_type_id')) if isinstance(data.get('subscription_type_id'), str) else data.get('subscription_type_id')
                amount: Decimal = Decimal(str(data.get('amount', 0)))
                currency: OrdersCurrency = OrdersCurrency(data.get('currency')) if isinstance(data.get('currency'), str) else data.get('currency', OrdersCurrency.INR)
                status: OrderStatus = OrderStatus(data.get('status')) if isinstance(data.get('status'), str) else data.get('status', OrderStatus.PENDING)
                payment_method: str = data.get('payment_method')
                payment_provider_id: str = data.get('payment_provider_id')
                paid_at: datetime = datetime.fromisoformat(data['paid_at']) if data.get('paid_at') else None if isinstance(data.get('paid_at'), str) else data.get('paid_at')
                order: Orders = Orders(
                    user_id=user_id,
                    subscription_id=subscription_id,
                    subscription_type_id=subscription_type_id,
                    amount=amount,
                    currency=currency,
                    status=status,
                    payment_method=payment_method,
                    payment_provider_id=payment_provider_id,
                    paid_at=paid_at
                )
                orders.append(order)
            session.add_all(orders)
            session.flush()
            result_data: List[Dict[str, Any]] = [order.to_dict() for order in orders]
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Created {len(orders)} orders successfully", 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Invalid ID format")
        except IntegrityError as e:
            logger.error(f"Integrity error creating orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error creating orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """Update orders based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Orders)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Orders, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Orders, key) == converted_value)
            # Prepare update data
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                # do not update id, created_at, user_id: even by accident.
                if hasattr(Orders, key) and key not in ['id', 'created_at', 'user_id'] and value is not None:
                    update_data[key] = self._convert_update_value(key, value)
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.now(timezone.utc)
            # Perform update
            updated_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Updated {updated_count} orders successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        """Update multiple orders with different data"""
        try:
            session: Session = self._get_session()
            updated_count: int = 0
            for update_item in updates:
                filters: Dict[str, Any] = update_item.get('filters', {})
                data: Dict[str, Any] = update_item.get('data', {})
                query: Query = session.query(Orders)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(Orders, key):
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(Orders, key) == converted_value)
                # Prepare update data
                update_data: Dict[str, Any] = {}
                for key, value in data.items():
                    # do not update id, created_at, user_id: even by accident.
                    if hasattr(Orders, key) and key not in ['id', 'created_at', 'user_id'] and value is not None:
                        update_data[key] = self._convert_update_value(key, value)
                # Add updated_at timestamp
                update_data['updated_at'] = datetime.now(timezone.utc)
                # Perform update
                count: int = query.update(update_data, synchronize_session=False)
                updated_count += count
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Updated {updated_count} orders successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating multiple orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Invalid ID or amount format")
        except IntegrityError as e:
            logger.error(f"Integrity error updating multiple orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating multiple orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """Delete orders based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Orders)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Orders, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Orders, key) == converted_value)
            # Perform delete
            deleted_count: int = query.delete(synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()  # this is where we synchronize the session.
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} orders successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """Delete multiple orders with different filters"""
        try:
            session: Session = self._get_session()
            deleted_count: int = 0
            for filters in filter_list:
                query: Query = session.query(Orders)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(Orders, key):
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(Orders, key) == converted_value)
                # Perform delete
                count: int = query.delete(synchronize_session=False)
                deleted_count += count
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} orders successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting multiple orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting multiple orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
