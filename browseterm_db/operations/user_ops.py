"""
User operations - Database operations for User model
"""

# builtins
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

# sqlalchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, Query

# local
from browseterm_db.models.users import User, AuthProvider
from browseterm_db.operations import DBOperations, OperationResult


logger = logging.getLogger(__name__)


class UserOps(DBOperations):
    """
    User operations implementing DBOperations abstract class
    """

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'provider': lambda value: value.name if isinstance(value, AuthProvider) else value,
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        """Convert insert values to appropriate types"""
        insert_conversion_map: dict = {
            'provider': lambda value: value.value if isinstance(value, AuthProvider) else value,
            'last_login': lambda value: datetime.fromisoformat(value) if value and isinstance(value, str) else value,
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update values to appropriate types"""
        update_conversion_map: dict = {
            'provider': lambda value: value.value if isinstance(value, AuthProvider) else value,
            'last_login': lambda value: datetime.fromisoformat(value) if value and isinstance(value, str) else value,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def find(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        to_dict: bool = True
    ) -> OperationResult:
        """Find multiple users based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters
            for key, value in filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            users: List[User] = query.all()
            user_list: List[Dict[str, Any]] = [user.to_dict() for user in users] if to_dict else users
            self._close_session()
            return OperationResult(
                success=True, 
                message=f"Found {len(user_list)} users", 
                data=user_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any], to_dict: bool = True) -> OperationResult:
        """Find a single user based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters
            for key, value in filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            user: User = query.first()
            result_data: Dict[str, Any] | None = None
            message: str = "User not found"
            if user:
                result_data: Dict[str, Any] = user.to_dict() if to_dict else user
                message: str = "User found"
            self._close_session()
            return OperationResult(
                success=True, 
                message=message, 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error finding user: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding user: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single user"""
        try:
            session: Session = self._get_session()
            # Handle provider enum
            provider: AuthProvider = AuthProvider(data.get('provider')) if isinstance(data.get('provider'), str) else data.get('provider')
            last_login: datetime | None = self._convert_insert_value('last_login', data.get('last_login'))
            # Create user instance
            user: User = User(
                email=data.get('email'),
                provider=provider,
                provider_id=data.get('provider_id'),
                last_login=last_login,
                is_active=data.get('is_active', True)
            )
            session.add(user)
            session.flush()  # Get the ID without committing
            result_data: Dict[str, Any] = user.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message="User created successfully", 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating user: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating user: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="User with this email already exists")
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple users"""
        raise NotImplementedError("Inserting multiple users is not implemented")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """Update users based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters
            for key, value in filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            # Prepare update data
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                if hasattr(User, key) and key not in ['id', 'created_at']:
                    converted_value = self._convert_update_value(key, value)
                    update_data[key] = converted_value
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.now(timezone.utc)
            # Perform update
            updated_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Updated {updated_count} users successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Update multiple users"""
        raise NotImplementedError("Updating multiple users is not implemented")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """Delete users based on filters (permanently removes from database)"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters
            for key, value in filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            # Get users to delete first (needed for cascade to work)
            users_to_delete: List[User] = query.all()
            deleted_count: int = len(users_to_delete)
            # Delete each user individually to trigger SQLAlchemy cascades
            for user in users_to_delete:
                session.delete(user)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} users successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def deactivate(self, filters: Dict[str, Any]) -> OperationResult:
        """Deactivate users based on filters (sets is_active = False)"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters
            for key, value in filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            # Perform soft delete by setting is_active = False
            update_data: Dict[str, Any] = {
                'is_active': False,
                'updated_at': datetime.now(timezone.utc)
            }
            deactivated_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deactivated {deactivated_count} users successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deactivating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deactivating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def reactivate(self, filters: Dict[str, Any]) -> OperationResult:
        """Reactivate users based on filters (sets is_active = True)"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters
            for key, value in filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            # Restore by setting is_active = True
            update_data: Dict[str, Any] = {
                'is_active': True,
                'updated_at': datetime.now(timezone.utc)
            }
            reactivated_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Reactivated {reactivated_count} users successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error reactivating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error reactivating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error reactivating users: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """Delete multiple users"""
        raise NotImplementedError("Deleting multiple users is not implemented")

    def get_user_containers(self, user_filters: Dict[str, Any]) -> OperationResult:
        """Get containers for a specific user"""
        try:
            """
            If user is not provided, find the user using filters.
            This is to prevent repeated queries for the same user. If you already have the user, you can pass it directly.
            """
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters to find the user
            for key, value in user_filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            user: User = query.first()
            containers_data: List[Dict[str, Any]] = []
            message: str = "User not found"
            if user and user.containers:
                containers_data = [container.to_dict() for container in user.containers]
                message = f"Found {len(containers_data)} containers for user"
            self._close_session()
            return OperationResult(
                success=True, 
                message=message, 
                data=containers_data
            )
        except ValueError as e:
            logger.error(f"Value Error getting user containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error getting user containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def get_user_orders(self, user_filters: Dict[str, Any]) -> OperationResult:
        """Get orders for a specific user"""
        try:
            """
            If user is not provided, find the user using filters.
            This is to prevent repeated queries for the same user. If you already have the user, you can pass it directly.
            """
            session: Session = self._get_session()
            query: Query = session.query(User)            
            # Apply filters to find the user
            for key, value in user_filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            user: User = query.first()
            orders_data: List[Dict[str, Any]] = []
            message: str = "User not found"
            if user and user.orders:
                orders_data = [order.to_dict() for order in user.orders]
                message = f"Found {len(orders_data)} orders for user"
            self._close_session()
            return OperationResult(
                success=True, 
                message=message, 
                data=orders_data
            )
        except ValueError as e:
            logger.error(f"Value Error getting user orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error getting user orders: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def get_user_subscription(self, user_filters: Dict[str, Any]) -> OperationResult:
        """Get subscription for a specific user"""
        try:
            """
            If user is not provided, find the user using filters.
            This is to prevent repeated queries for the same user. If you already have the user, you can pass it directly.
            """
            session: Session = self._get_session()
            query: Query = session.query(User)
            # Apply filters to find the user
            for key, value in user_filters.items():
                if hasattr(User, key):
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(User, key) == converted_value)
            user: User = query.first()
            subscription_data: Dict[str, Any] = {}
            message: str = "User not found"
            if user and user.subscription:
                subscription_data = user.subscription.to_dict() if user.subscription else None
                message = "Found user subscription" if subscription_data else "User has no subscription"
            self._close_session()
            return OperationResult(
                success=True, 
                message=message, 
                data=subscription_data
            )
        except ValueError as e:
            logger.error(f"Value Error getting user subscription: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error getting user subscription: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
