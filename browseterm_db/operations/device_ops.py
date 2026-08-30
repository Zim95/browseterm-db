"""
Device operations - Database operations for Device model
"""
# builtins
import uuid
from datetime import datetime, timezone
import logging

# sqlalchemy
from typing import Dict, List, Any, Optional
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import Query

# local
from browseterm_db.models.devices import Device, DeviceStatus
from browseterm_db.operations import DBOperations, OperationResult


logger = logging.getLogger(__name__)


class DeviceOps(DBOperations):
    """
    Device operations implementing DBOperations abstract class
    """

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'status': lambda value: value if isinstance(value, DeviceStatus) else DeviceStatus(value),
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update values to appropriate types"""
        update_conversion_map: dict = {
            'status': lambda value: value if isinstance(value, DeviceStatus) else DeviceStatus(value),
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        """Convert insert values to appropriate types"""
        insert_conversion_map: dict = {
            'status': lambda value: value if isinstance(value, DeviceStatus) else DeviceStatus(value),
            'user_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None,
             offset: Optional[int] = None) -> OperationResult:
        """Find multiple devices based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Device)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Device, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Device, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            devices: List[Device] = query.all()
            result_list: List[Dict[str, Any]] = [device.to_dict() for device in devices]
            self._close_session()
            return OperationResult(
                success=True,
                message=f"Found {len(result_list)} devices",
                data=result_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        """Find a single device based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Device)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Device, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Device, key) == converted_value)
            device: Device = query.first()
            result_data: Dict[str, Any] | None = None
            message: str = "Device not found"
            if device:
                result_data = device.to_dict()
                message = "Device found"
            self._close_session()
            return OperationResult(
                success=True,
                message=message,
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error finding device: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding device: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single device"""
        try:
            session: Session = self._get_session()
            user_id: uuid.UUID = self._convert_insert_value('user_id', data.get('user_id'))
            status: DeviceStatus = self._convert_insert_value('status', data.get('status', DeviceStatus.ACTIVE))
            device: Device = Device(
                user_id=user_id,
                device_name=data.get('device_name'),
                os=data.get('os'),
                architecture=data.get('architecture'),
                runtime_version=data.get('runtime_version'),
                total_cpu=data.get('total_cpu'),
                total_memory_bytes=data.get('total_memory_bytes'),
                total_storage_bytes=data.get('total_storage_bytes'),
                allocated_cpu=data.get('allocated_cpu'),
                allocated_memory_bytes=data.get('allocated_memory_bytes'),
                allocated_storage_bytes=data.get('allocated_storage_bytes'),
                used_cpu=data.get('used_cpu', 0),
                used_memory_bytes=data.get('used_memory_bytes', 0),
                used_storage_bytes=data.get('used_storage_bytes', 0),
                gpu_info=data.get('gpu_info'),
                status=status,
            )
            session.add(device)
            session.flush()  # Get the ID without committing
            result_data: Dict[str, Any] = device.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message="Device created successfully",
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating device: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating device: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="User not found or device name already registered for this user")
        except SQLAlchemyError as e:
            logger.error(f"Error creating device: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple devices"""
        raise NotImplementedError("Inserting multiple devices is not implemented")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """Update devices based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Device)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Device, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Device, key) == converted_value)
            # Prepare update data. A None value here means "set this column to NULL"
            # (e.g. clearing last_seen_at) -- only keys the caller omitted entirely are
            # left untouched.
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                if hasattr(Device, key) and key not in ['id', 'registered_at', 'user_id']:
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
                message=f"Updated {updated_count} devices successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        """Update multiple devices with different data"""
        raise NotImplementedError("Update multiple devices is not implemented")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """Delete devices based on filters (hard delete)"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(Device)
            # Apply filters
            for key, value in filters.items():
                if hasattr(Device, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(Device, key) == converted_value)
            # Perform hard delete (permanently remove from database)
            deleted_count: int = query.delete(synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Deleted {deleted_count} devices successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """Delete multiple devices with different filters (hard delete)"""
        try:
            session: Session = self._get_session()
            deleted_count: int = 0
            for filters in filter_list:
                query: Query = session.query(Device)
                # Apply filters
                for key, value in filters.items():
                    if hasattr(Device, key) and value is not None:
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(Device, key) == converted_value)
                # Perform hard delete (permanently remove from database)
                count: int = query.delete(synchronize_session=False)
                deleted_count += count
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Deleted {deleted_count} devices successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting multiple devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting multiple devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple devices: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
