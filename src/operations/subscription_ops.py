"""
Subscription operations - Database operations for Subscription model
"""
# builtins
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

# sqlalchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, Query

# local
from src.models.subscriptions import Subscription, SubscriptionStatus
from . import DBOperations, OperationResult


logger = logging.getLogger(__name__)

DEFAULT_DURATION_DAYS: int = 30


class SubscriptionOps(DBOperations):
    """
    Subscription operations implementing DBOperations abstract class
    """

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        """Convert insert values to appropriate types"""
        insert_conversion_map: dict = {
            'valid_until': lambda value: datetime.fromisoformat(value) if isinstance(value, str) else value,
            'cancelled_at': lambda value: datetime.fromisoformat(value) if isinstance(value, str) else value,
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'subscription_type_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'subscription_type_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update values to appropriate types"""
        update_conversion_map: dict = {
            'valid_until': lambda value: datetime.fromisoformat(value) if isinstance(value, str) else value,
            'cancelled_at': lambda value: datetime.fromisoformat(value) if isinstance(value, str) else value,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None, 
             offset: Optional[int] = None) -> OperationResult:
        """Find multiple subscriptions based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Subscription)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Subscription, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Subscription, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            subscriptions: List[Subscription] = query.all()
            result_list: List[Dict[str, Any]] = [subscription.to_dict() for subscription in subscriptions]
            self._close_session()
            return OperationResult(
                success=True, 
                message=f"Found {len(result_list)} subscriptions", 
                data=result_list
            )
        except SQLAlchemyError as e:
            logger.error(f"Error finding subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        """Find a single subscription based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Subscription)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Subscription, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Subscription, key) == converted_value)
            subscription: Subscription = query.first()
            result_data: Dict[str, Any] | None = None
            message: str = "Subscription not found"
            if subscription:
                result_data = subscription.to_dict()
                message = "Subscription found"
            self._close_session()
            return OperationResult(
                success=True, 
                message=message, 
                data=result_data
            )
        except SQLAlchemyError as e:
            logger.error(f"Error finding subscription: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single subscription"""
        try:
            session: Session = self._get_session()
            # Convert UUIDs if they're strings
            user_id: uuid.UUID = self._convert_insert_value('user_id', data.get('user_id'))
            subscription_type_id: uuid.UUID = self._convert_insert_value('subscription_type_id', data.get('subscription_type_id'))
            # Calculate valid_until based on subscription type duration
            valid_until: datetime | None = self._convert_insert_value('valid_until', data.get('valid_until'))
            if not valid_until:
                # Get subscription type to calculate valid_until
                from src.models.subscription_types import SubscriptionType
                sub_type = session.query(SubscriptionType).filter(
                    SubscriptionType.id == subscription_type_id
                ).first()
                duration_days: int = sub_type.duration_days if sub_type else DEFAULT_DURATION_DAYS
                valid_until = datetime.now(timezone.utc) + timedelta(days=duration_days)
            cancelled_at: datetime | None = self._convert_insert_value('cancelled_at', data.get('cancelled_at'))
            # Create subscription instance
            subscription = Subscription(
                user_id=user_id,
                subscription_type_id=subscription_type_id,
                status=data.get('status', SubscriptionStatus.PENDING),
                auto_renew=data.get('auto_renew', True),
                valid_until=valid_until,
                cancelled_at=cancelled_at
            )
            session.add(subscription)
            session.flush()  # Get the ID without committing
            result_data: Dict[str, Any] = subscription.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message="Subscription created successfully", 
                data=result_data
            )   
        except ValueError as e:
            logger.error(f"Invalid UUID format: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Invalid ID format")
        except IntegrityError as e:
            logger.error(f"Integrity error creating subscription: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="User already has a subscription or invalid references")
        except SQLAlchemyError as e:
            logger.error(f"Error creating subscription: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple subscriptions"""
        raise NotImplementedError("Inserting multiple subscriptions is not implemented")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """Update subscriptions based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Subscription)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Subscription, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Subscription, key) == converted_value)
            # Prepare update data
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                if hasattr(Subscription, key) and key not in ['id', 'created_at', 'user_id']:
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
                message=f"Updated {updated_count} subscriptions successfully"
            )   
        except ValueError as e:
            logger.error(f"Invalid UUID or datetime format: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Invalid ID or datetime format")
        except SQLAlchemyError as e:
            logger.error(f"Error updating subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
    
    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        """Update multiple subscriptions with different data"""
        raise NotImplementedError("Updating multiple subscriptions is not implemented")
    
    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """
        Hard delete subscriptions based on filters (CASCADE DELETE)
        WARNING: This will also delete all related orders!
        Use soft_delete() for normal operations.
        """
        try:
            session: Session = self._get_session()
            query: Query = session.query(Subscription)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Subscription, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Subscription, key) == converted_value)
            # Get subscriptions to delete first (needed for cascade to work)
            subscriptions_to_delete: List[Subscription] = query.all()
            deleted_count: int = len(subscriptions_to_delete)
            # Delete each subscription individually to trigger SQLAlchemy cascades
            for subscription in subscriptions_to_delete:
                session.delete(subscription)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} subscriptions successfully"
            )    
        except ValueError as e:
            logger.error(f"Invalid UUID format: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Invalid ID format")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def soft_delete(self, filters: Dict[str, Any]) -> OperationResult:
        """
        Soft delete subscriptions by setting status=CANCELLED and cancelled_at=now()
        This preserves historical data and relationships.
        Recommended for UI operations.
        """
        try:
            session: Session = self._get_session()
            query: Query = session.query(Subscription)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Subscription, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Subscription, key) == converted_value)
            # Prepare update data for soft delete
            update_data: Dict[str, Any] = {
                'status': SubscriptionStatus.CANCELLED,
                'cancelled_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            # Perform soft delete (update)
            deleted_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Soft deleted {deleted_count} subscriptions successfully"
            )
        except ValueError as e:
            logger.error(f"Invalid UUID format: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Invalid ID format")
        except SQLAlchemyError as e:
            logger.error(f"Error soft deleting subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """
        Hard delete multiple subscriptions with different filters (CASCADE DELETE)
        WARNING: This will also delete all related orders!
        Use soft_delete_many() for normal operations.
        """
        try:
            session: Session = self._get_session()
            deleted_count: int = 0
            for filters in filter_list:
                query: Query = session.query(Subscription)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(Subscription, key):
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(Subscription, key) == converted_value)
                # Get subscriptions to delete first (needed for cascade to work)
                subscriptions_to_delete: List[Subscription] = query.all()
                # Delete each subscription individually to trigger SQLAlchemy cascades
                for subscription in subscriptions_to_delete:
                    session.delete(subscription)
                    deleted_count += 1
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} subscriptions successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting multiple subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def soft_delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """
        Soft delete multiple subscriptions by setting status=CANCELLED and cancelled_at=now()
        This preserves historical data and relationships.
        Recommended for UI operations.
        """
        try:
            session: Session = self._get_session()
            updated_count: int = 0
            for filters in filter_list:
                query: Query = session.query(Subscription)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(Subscription, key):
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(Subscription, key) == converted_value)
                # Prepare update data for soft delete
                update_data: Dict[str, Any] = {
                    'status': SubscriptionStatus.CANCELLED,
                    'cancelled_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
                # Perform soft delete (update)
                count: int = query.update(update_data, synchronize_session=False)
                updated_count += count
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Soft deleted {updated_count} subscriptions successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error soft deleting multiple subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error soft deleting multiple subscriptions: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
