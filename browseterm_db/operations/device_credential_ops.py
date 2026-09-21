"""
DeviceCredential operations - Database operations for DeviceCredential model (Part 1 schema;
wiring actual token issuance/validation to this table is Part 4 work).
"""
# builtins
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

# sqlalchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Query, Session

# local
from browseterm_db.models.device_credentials import DeviceCredential
from browseterm_db.operations import DBOperations, OperationResult


logger = logging.getLogger(__name__)


class DeviceCredentialOps(DBOperations):
    """DeviceCredential operations implementing DBOperations abstract class."""

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        filter_conversion_map: dict = {'device_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v}
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        _parse_datetime = lambda v: datetime.fromisoformat(v) if isinstance(v, str) else v
        update_conversion_map: dict = {
            'last_used_at': _parse_datetime, 'rotated_at': _parse_datetime, 'revoked_at': _parse_datetime,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        insert_conversion_map: dict = {'device_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v}
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None,
             offset: Optional[int] = None) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCredential)
            for key, value in filters.items():
                if hasattr(DeviceCredential, key) and value is not None:
                    query = query.filter(getattr(DeviceCredential, key) == self._convert_filter_value(key, value))
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            rows: List[DeviceCredential] = query.all()
            result_list = [r.to_dict() for r in rows]
            self._close_session()
            return OperationResult(success=True, message=f"Found {len(result_list)} credentials", data=result_list)
        except SQLAlchemyError as e:
            logger.error(f"Error finding credentials: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCredential)
            for key, value in filters.items():
                if hasattr(DeviceCredential, key) and value is not None:
                    query = query.filter(getattr(DeviceCredential, key) == self._convert_filter_value(key, value))
            row: DeviceCredential = query.first()
            result_data = row.to_dict() if row else None
            message = "Credential found" if row else "Credential not found"
            self._close_session()
            return OperationResult(success=True, message=message, data=result_data)
        except SQLAlchemyError as e:
            logger.error(f"Error finding credential: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """`data` must include a pre-hashed `token_hash` - this layer never hashes or sees the
        raw token itself, that responsibility stays entirely with the caller (Part 4)."""
        try:
            session: Session = self._get_session()
            row = DeviceCredential(
                device_id=self._convert_insert_value('device_id', data.get('device_id')),
                token_prefix=data.get('token_prefix'),
                token_hash=data.get('token_hash'),
            )
            session.add(row)
            session.flush()
            result_data = row.to_dict()
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message="Credential created successfully", data=result_data)
        except IntegrityError as e:
            logger.error(f"Integrity error creating credential: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Device not found")
        except SQLAlchemyError as e:
            logger.error(f"Error creating credential: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        raise NotImplementedError("Inserting multiple credentials is not implemented")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCredential)
            for key, value in filters.items():
                if hasattr(DeviceCredential, key) and value is not None:
                    query = query.filter(getattr(DeviceCredential, key) == self._convert_filter_value(key, value))
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                if hasattr(DeviceCredential, key) and key not in ['id', 'created_at', 'device_id']:
                    update_data[key] = self._convert_update_value(key, value) if value is not None else None
            updated_count: int = query.update(update_data, synchronize_session=False)
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message=f"Updated {updated_count} credentials successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error updating credentials: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        raise NotImplementedError("Update multiple credentials is not implemented")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCredential)
            for key, value in filters.items():
                if hasattr(DeviceCredential, key) and value is not None:
                    query = query.filter(getattr(DeviceCredential, key) == self._convert_filter_value(key, value))
            deleted_count: int = query.delete(synchronize_session=False)
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message=f"Deleted {deleted_count} credentials successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting credentials: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        try:
            session: Session = self._get_session()
            deleted_count = 0
            for filters in filter_list:
                query: Query = session.query(DeviceCredential)
                for key, value in filters.items():
                    if hasattr(DeviceCredential, key) and value is not None:
                        query = query.filter(getattr(DeviceCredential, key) == self._convert_filter_value(key, value))
                deleted_count += query.delete(synchronize_session=False)
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message=f"Deleted {deleted_count} credentials successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple credentials: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
