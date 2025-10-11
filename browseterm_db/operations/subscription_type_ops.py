"""
SubscriptionType operations - Database operations for SubscriptionType model
"""
# builtins
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from decimal import Decimal

# sqlalchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, Query

# local
from browseterm_db.models.subscription_types import SubscriptionType, SubscriptionTypeCurrency
from browseterm_db.operations import DBOperations, OperationResult
from browseterm_db.models.containers import DEFAULT_CPU_LIMIT, DEFAULT_MEMORY_LIMIT


logger = logging.getLogger(__name__)


class SubscriptionTypeOps(DBOperations):
    """
    SubscriptionType operations implementing DBOperations abstract class
    """

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter value to appropriate type"""
        filter_conversion_map: dict = {
            'currency': lambda value: value.value if isinstance(value, SubscriptionTypeCurrency) else value,
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update value to appropriate type"""
        update_conversion_map: dict = {
            'currency': lambda value: value if isinstance(value, SubscriptionTypeCurrency) else SubscriptionTypeCurrency(value),
            'amount': lambda value: Decimal(str(value)) if value is not None else None,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        """Convert insert value to appropriate type"""
        insert_conversion_map: dict = {
            'currency': lambda value: value if isinstance(value, SubscriptionTypeCurrency) else SubscriptionTypeCurrency(value),
            'amount': lambda value: Decimal(str(value)) if value is not None else None,
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'currency': lambda value: value.name if isinstance(value, SubscriptionTypeCurrency) else value,
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None, 
             offset: Optional[int] = None) -> OperationResult:
        """Find multiple subscription types based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(SubscriptionType)
            # Apply filters
            for key, value in filters.items():
                if hasattr(SubscriptionType, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(SubscriptionType, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            subscription_types: List[SubscriptionType] = query.all()
            result_list: List[Dict[str, Any]] = [sub_type.to_dict() for sub_type in subscription_types]
            self._close_session()
            return OperationResult(
                success=True, 
                message=f"Found {len(result_list)} subscription types", 
                data=result_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        """Find a single subscription type based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(SubscriptionType)
            # Apply filters
            for key, value in filters.items():
                if hasattr(SubscriptionType, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(SubscriptionType, key) == converted_value)
            subscription_type: SubscriptionType = query.first()
            result_data: Dict[str, Any] | None = None
            message: str = "Subscription type not found"
            if subscription_type:
                result_data = subscription_type.to_dict()
                message = "Subscription type found"
            self._close_session()
            return OperationResult(
                success=True, 
                message=message, 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error finding subscription type: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding subscription type: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single subscription type"""
        try:
            session: Session = self._get_session()
            # Create subscription type instance
            subscription_type: SubscriptionType = SubscriptionType(
                name=data.get('name'),
                type=data.get('type'),
                amount=Decimal(str(data.get('amount'))),
                currency=SubscriptionTypeCurrency(data.get('currency')) if isinstance(data.get('currency'), str) else data.get('currency', SubscriptionTypeCurrency.INR),
                duration_days=data.get('duration_days', 30),
                extra_message=data.get('extra_message'),
                max_containers=data.get('max_containers', 1),
                cpu_limit_per_container=data.get('cpu_limit_per_container', DEFAULT_CPU_LIMIT),
                memory_limit_per_container=data.get('memory_limit_per_container', DEFAULT_MEMORY_LIMIT),
                description=data.get('description'),
                is_active=data.get('is_active', True)
            )
            session.add(subscription_type)
            session.flush()  # Get the ID without committing
            result_data: Dict[str, Any] = subscription_type.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message="Subscription type created successfully", 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating subscription type: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating subscription type: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error creating subscription type: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple subscription types"""
        try:
            session: Session = self._get_session()
            subscription_types: List[SubscriptionType] = []
            for data in data_list:
                subscription_type: SubscriptionType = SubscriptionType(
                    name=data.get('name'),
                    type=data.get('type'),
                    amount=Decimal(str(data.get('amount', 0))),
                    currency=SubscriptionTypeCurrency(data.get('currency')) if isinstance(data.get('currency'), str) else data.get('currency', SubscriptionTypeCurrency.INR),
                    duration_days=data.get('duration_days', 30),
                    extra_message=data.get('extra_message'),
                    max_containers=data.get('max_containers', 1),
                    cpu_limit_per_container=data.get('cpu_limit_per_container', DEFAULT_CPU_LIMIT),
                    memory_limit_per_container=data.get('memory_limit_per_container', DEFAULT_MEMORY_LIMIT),
                    description=data.get('description'),
                    is_active=data.get('is_active', True)
                )
                subscription_types.append(subscription_type)
            session.add_all(subscription_types)
            session.flush()
            result_data: List[Dict[str, Any]] = [sub_type.to_dict() for sub_type in subscription_types]
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Created {len(subscription_types)} subscription types successfully", 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error creating subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """Update subscription types based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(SubscriptionType)
            # Apply filters
            for key, value in filters.items():
                if hasattr(SubscriptionType, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(SubscriptionType, key) == converted_value)
            # Prepare update data
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                # id and created_at are not updatable, even by accident.
                if hasattr(SubscriptionType, key) and key not in ['id', 'created_at']:
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
                message=f"Updated {updated_count} subscription types successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        """Update multiple subscription types with different data"""
        try:
            session: Session = self._get_session()
            updated_count: int = 0
            for update_item in updates:
                filters: Dict[str, Any] = update_item.get('filters', {})
                data: Dict[str, Any] = update_item.get('data', {})
                query: Query = session.query(SubscriptionType)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(SubscriptionType, key):
                        query = query.filter(getattr(SubscriptionType, key) == value)
                # Prepare update data
                update_data: Dict[str, Any] = {}
                for key, value in data.items():
                    # id and created_at are not updatable, even by accident.
                    if hasattr(SubscriptionType, key) and key not in ['id', 'created_at']:
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
                message=f"Updated {updated_count} subscription types successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """
        Hard delete subscription types based on filters (CASCADE DELETE)
        WARNING: This will also delete all related subscriptions and orders!
        Use soft_delete() for normal operations.
        """
        try:
            session: Session = self._get_session()
            query: Query = session.query(SubscriptionType)
            # Apply filters
            for key, value in filters.items():
                if hasattr(SubscriptionType, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(SubscriptionType, key) == converted_value)
            # Get subscription types to delete first (needed for cascade to work)
            subscription_types_to_delete: List[SubscriptionType] = query.all()
            deleted_count: int = len(subscription_types_to_delete)
            # Delete each subscription type individually to trigger SQLAlchemy cascades
            for subscription_type in subscription_types_to_delete:
                session.delete(subscription_type)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} subscription types successfully"
            )   
        except ValueError as e:
            logger.error(f"Value Error deleting subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """
        Hard delete multiple subscription types with different filters (CASCADE DELETE)
        WARNING: This will also delete all related subscriptions and orders!
        Use soft_delete_many() for normal operations.
        """
        try:
            session: Session = self._get_session()
            deleted_count: int = 0
            for filters in filter_list:
                query: Query = session.query(SubscriptionType)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(SubscriptionType, key):
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(SubscriptionType, key) == converted_value)
                # Get subscription types to delete first (needed for cascade to work)
                subscription_types_to_delete: List[SubscriptionType] = query.all()
                # Delete each subscription type individually to trigger SQLAlchemy cascades
                for subscription_type in subscription_types_to_delete:
                    session.delete(subscription_type)
                    deleted_count += 1
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} subscription types successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def soft_delete(self, filters: Dict[str, Any]) -> OperationResult:
        """
        Soft delete subscription types by setting is_active=False
        This preserves historical data and relationships.
        Recommended for UI operations.
        """
        try:
            session: Session = self._get_session()
            query: Query = session.query(SubscriptionType)
            # Apply filters
            for key, value in filters.items():
                if hasattr(SubscriptionType, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(SubscriptionType, key) == converted_value)
            # Prepare update data for soft delete
            update_data: Dict[str, Any] = {
                'is_active': False,
                'updated_at': datetime.now(timezone.utc)
            }
            # Perform soft delete (update)
            updated_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Soft deleted {updated_count} subscription types successfully"
            )   
        except ValueError as e:
            logger.error(f"Value Error soft deleting subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error soft deleting subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error soft deleting subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def soft_delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """
        Soft delete multiple subscription types by setting is_active=False
        This preserves historical data and relationships.
        Recommended for UI operations.
        """
        try:
            session: Session = self._get_session()
            updated_count: int = 0
            for filters in filter_list:
                query: Query = session.query(SubscriptionType)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(SubscriptionType, key):
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(SubscriptionType, key) == converted_value)
                # Prepare update data for soft delete
                update_data: Dict[str, Any] = {
                    'is_active': False,
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
                message=f"Soft deleted {updated_count} subscription types successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error soft deleting multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error soft deleting multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error soft deleting multiple subscription types: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
