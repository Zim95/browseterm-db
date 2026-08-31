"""
Container operations - Database operations for Container model
"""
# builtins
import uuid
from datetime import datetime, timezone, timedelta
import logging

# sqlalchemy
from typing import Dict, List, Any, Optional
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import Query

# local
from browseterm_db.models.containers import Container, ContainerStatus, SaveStatus
from browseterm_db.operations import DBOperations, OperationResult
from browseterm_db.models.containers import DEFAULT_CPU_LIMIT, DEFAULT_MEMORY_LIMIT, DEFAULT_STORAGE_LIMIT


logger = logging.getLogger(__name__)


class ContainerOps(DBOperations):
    """
    Container operations implementing DBOperations abstract class
    """

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'image_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'device_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update values to appropriate types"""
        update_conversion_map: dict = {
            'status': lambda value: value if isinstance(value, ContainerStatus) else ContainerStatus(value),
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'image_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'device_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        """Convert insert values to appropriate types"""
        insert_conversion_map: dict = {
            'status': lambda value: value if isinstance(value, ContainerStatus) else ContainerStatus(value),
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'image_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'device_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None, 
             offset: Optional[int] = None) -> OperationResult:
        """Find multiple containers based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Container)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Container, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Container, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            containers: List[Container] = query.all()
            result_list: List[Dict[str, Any]] = [container.to_dict() for container in containers]
            self._close_session()
            return OperationResult(
                success=True, 
                message=f"Found {len(result_list)} containers", 
                data=result_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_idle_containers(self, threshold_seconds: int, device_id: Optional[str] = None) -> OperationResult:
        """Find RUNNING containers whose last_active_at is older than the idle threshold.

        Used by the reaper to pick containers to hibernate. Containers with a null
        last_active_at are treated as not-yet-tracked and are NOT returned.

        P18 (see ~/browseterm/p.md's "P18" section): `device_id`, when given, scopes this to only
        that device's containers - "the reaper must operate only on containers whose device_id is
        the current device" (plan section 16). Optional and defaulting to None (no filter) so the
        existing signature/behavior is unchanged for any other caller.
        """
        try:
            session: Session = self._get_session()
            cutoff: datetime = datetime.now(timezone.utc) - timedelta(seconds=threshold_seconds)
            filters = [
                Container.status == ContainerStatus.RUNNING,
                Container.last_active_at.isnot(None),
                Container.last_active_at < cutoff,
            ]
            if device_id is not None:
                filters.append(Container.device_id == self._convert_filter_value('device_id', device_id))
            query: Query = session.query(Container).filter(*filters)
            containers: List[Container] = query.all()
            result_list: List[Dict[str, Any]] = [container.to_dict() for container in containers]
            self._close_session()
            return OperationResult(
                success=True,
                message=f"Found {len(result_list)} idle containers",
                data=result_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding idle containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding idle containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_stuck_saves(self) -> OperationResult:
        """Find all containers whose save_status is Pending or Running.

        These are in-progress saves as far as the DB knows. Used by container-maker's save
        reconciler to find candidates that may have been orphaned by a dead/evicted snapshot
        Job -- it still has to check each one's actual Job state before deciding anything is
        really stuck (a fresh save is legitimately Pending/Running for a while).
        """
        try:
            session: Session = self._get_session()
            query: Query = session.query(Container).filter(
                Container.save_status.in_([SaveStatus.PENDING.value, SaveStatus.RUNNING.value]),
            )
            containers: List[Container] = query.all()
            result_list: List[Dict[str, Any]] = [container.to_dict() for container in containers]
            self._close_session()
            return OperationResult(
                success=True,
                message=f"Found {len(result_list)} in-progress saves",
                data=result_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding stuck saves: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding stuck saves: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        """Find a single container based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Container)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Container, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Container, key) == converted_value)
            container: Container = query.first()
            result_data: Dict[str, Any] | None = None
            message: str = "Container not found"
            if container:
                result_data = container.to_dict()
                message = "Container found"
            self._close_session()
            return OperationResult(
                success=True,
                message=message,
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error finding container: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding container: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single container"""
        try:
            session: Session = self._get_session()
            # Convert user_id to UUID if it's a string
            user_id: uuid.UUID = uuid.UUID(data.get('user_id')) if isinstance(data.get('user_id'), str) else data.get('user_id')
            # Convert image_id to UUID if it's a string
            image_id: uuid.UUID | None = uuid.UUID(data.get('image_id')) if isinstance(data.get('image_id'), str) else data.get('image_id')
            # Convert device_id to UUID if it's a string
            device_id: uuid.UUID | None = uuid.UUID(data.get('device_id')) if isinstance(data.get('device_id'), str) else data.get('device_id')
            # Handle status enum
            status: ContainerStatus = ContainerStatus(data.get('status', ContainerStatus.PENDING)) if isinstance(data.get('status'), str) else data.get('status')
            # Create container instance
            container: Container = Container(
                user_id=user_id,
                image_id=image_id,
                device_id=device_id,
                name=data.get('name'),
                status=status,
                cpu_limit=data.get('cpu_limit', DEFAULT_CPU_LIMIT),
                memory_limit=data.get('memory_limit', DEFAULT_MEMORY_LIMIT),
                storage_limit=data.get('storage_limit', DEFAULT_STORAGE_LIMIT),
                ip_address=data.get('ip_address'),
                port_mappings=data.get('port_mappings'),
                environment_vars=data.get('environment_vars'),
                associated_resources=data.get('associated_resources')
            )
            session.add(container)
            session.flush()  # Get the ID without committing
            result_data: Dict[str, Any] = container.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message="Container created successfully", 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating container: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating container: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="User not found")
        except SQLAlchemyError as e:
            logger.error(f"Error creating container: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple containers"""
        try:
            session: Session = self._get_session()
            containers: List[Container] = []
            for data in data_list:
                user_id: uuid.UUID = uuid.UUID(data.get('user_id')) if isinstance(data.get('user_id'), str) else data.get('user_id')
                image_id: uuid.UUID | None = uuid.UUID(data.get('image_id')) if isinstance(data.get('image_id'), str) else data.get('image_id')
                device_id: uuid.UUID | None = uuid.UUID(data.get('device_id')) if isinstance(data.get('device_id'), str) else data.get('device_id')
                status: ContainerStatus = ContainerStatus(data.get('status', ContainerStatus.PENDING)) if isinstance(data.get('status'), str) else data.get('status')
                container: Container = Container(
                    user_id=user_id,
                    image_id=image_id,
                    device_id=device_id,
                    name=data.get('name'),
                    status=status,
                    cpu_limit=data.get('cpu_limit', DEFAULT_CPU_LIMIT),
                    memory_limit=data.get('memory_limit', DEFAULT_MEMORY_LIMIT),
                    storage_limit=data.get('storage_limit', DEFAULT_STORAGE_LIMIT),
                    ip_address=data.get('ip_address'),
                    port_mappings=data.get('port_mappings'),
                    environment_vars=data.get('environment_vars'),
                    associated_resources=data.get('associated_resources')
                )
                containers.append(container)
            session.add_all(containers)
            session.flush()
            result_data: List[Dict[str, Any]] = [container.to_dict() for container in containers]
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Created {len(containers)} containers successfully", 
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error creating containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """Update containers based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Container)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Container, key) and value is not None:  # we added value is not None because none of the values are nullable in the container model.
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Container, key) == converted_value)
            # Prepare update data. Unlike the filters loop above, a None value here is NOT
            # "skip this field" -- callers (e.g. clearing save_error when a new save starts)
            # pass None explicitly meaning "set this column to NULL". Only keys the caller
            # omitted from `data` entirely are left untouched.
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                if hasattr(Container, key) and key not in ['id', 'created_at', 'user_id']:
                    update_data[key] = self._convert_update_value(key, value) if value is not None else None
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.now(timezone.utc)
            # Perform update
            updated_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Updated {updated_count} containers successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        """Update multiple containers with different data"""
        raise NotImplementedError("Update multiple containers is not implemented")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """Delete containers based on filters (hard delete)"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Container)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Container, key) and value is not None:  # 
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Container, key) == converted_value)
            # Perform hard delete (permanently remove from database)
            deleted_count: int = query.delete(synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()    
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} containers successfully"
            )   
        except ValueError as e:
            logger.error(f"Value Error deleting containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """Delete multiple containers with different filters (hard delete)"""
        try:
            session: Session = self._get_session()
            deleted_count: int = 0
            for filters in filter_list:
                query: Query = session.query(Container)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(Container, key) and value is not None:
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(Container, key) == converted_value)
                # Perform hard delete (permanently remove from database)
                count: int = query.delete(synchronize_session=False)
                deleted_count += count
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True, 
                message=f"Deleted {deleted_count} containers successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting multiple containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting multiple containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple containers: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
