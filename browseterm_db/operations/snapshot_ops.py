"""
Snapshot operations - Database operations for ContainerSnapshot model (P15)
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
from browseterm_db.models.container_snapshots import ContainerSnapshot, SnapshotStatus
from browseterm_db.operations import DBOperations, OperationResult


logger = logging.getLogger(__name__)


class SnapshotOps(DBOperations):
    """
    ContainerSnapshot operations implementing DBOperations abstract class
    """

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        """Convert filter values to appropriate types"""
        filter_conversion_map: dict = {
            'container_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
            'status': lambda value: value if isinstance(value, SnapshotStatus) else SnapshotStatus(value),
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        """Convert update values to appropriate types"""
        update_conversion_map: dict = {
            'status': lambda value: value if isinstance(value, SnapshotStatus) else SnapshotStatus(value),
            'container_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        """Convert insert values to appropriate types"""
        insert_conversion_map: dict = {
            'status': lambda value: value if isinstance(value, SnapshotStatus) else SnapshotStatus(value),
            'container_id': lambda value: uuid.UUID(value) if isinstance(value, str) else value,
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None,
             offset: Optional[int] = None) -> OperationResult:
        """Find multiple snapshots based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(ContainerSnapshot)
            # Apply filters
            for key, value in filters.items():
                if hasattr(ContainerSnapshot, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(ContainerSnapshot, key) == converted_value)
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            snapshots: List[ContainerSnapshot] = query.all()
            result_list: List[Dict[str, Any]] = [snapshot.to_dict() for snapshot in snapshots]
            self._close_session()
            return OperationResult(
                success=True,
                message=f"Found {len(result_list)} snapshots",
                data=result_list
            )
        except ValueError as e:
            logger.error(f"Value Error finding snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        """Find a single snapshot based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(ContainerSnapshot)
            # Apply filters
            for key, value in filters.items():
                if hasattr(ContainerSnapshot, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(ContainerSnapshot, key) == converted_value)
            snapshot: ContainerSnapshot = query.first()
            result_data: Dict[str, Any] | None = None
            message: str = "Snapshot not found"
            if snapshot:
                result_data = snapshot.to_dict()
                message = "Snapshot found"
            self._close_session()
            return OperationResult(
                success=True,
                message=message,
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error finding snapshot: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding snapshot: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Insert a single snapshot"""
        try:
            session: Session = self._get_session()
            container_id: uuid.UUID = self._convert_insert_value('container_id', data.get('container_id'))
            status: SnapshotStatus = self._convert_insert_value('status', data.get('status', SnapshotStatus.PENDING))
            snapshot: ContainerSnapshot = ContainerSnapshot(
                container_id=container_id,
                version_sequence=data.get('version_sequence'),
                version=data.get('version'),
                image_repository=data.get('image_repository'),
                image_reference=data.get('image_reference'),
                registry_digest=data.get('registry_digest'),
                request_id=data.get('request_id'),
                status=status,
                error_detail=data.get('error_detail'),
            )
            session.add(snapshot)
            session.flush()  # Get the ID without committing
            result_data: Dict[str, Any] = snapshot.to_dict()
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message="Snapshot created successfully",
                data=result_data
            )
        except ValueError as e:
            logger.error(f"Value Error creating snapshot: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating snapshot: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="Container not found, or a snapshot with this request_id/version_sequence already exists for this container")
        except SQLAlchemyError as e:
            logger.error(f"Error creating snapshot: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        """Insert multiple snapshots"""
        raise NotImplementedError("Inserting multiple snapshots is not implemented")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        """Update snapshots based on filters"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(ContainerSnapshot)
            # Apply filters
            for key, value in filters.items():
                if hasattr(ContainerSnapshot, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(ContainerSnapshot, key) == converted_value)
            # Build update data - explicit None values are preserved (not dropped), matching
            # ContainerOps.update()'s fix for the same class of bug (see p.md).
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                if hasattr(ContainerSnapshot, key) and key not in ['id', 'container_id', 'created_at']:
                    update_data[key] = self._convert_update_value(key, value) if value is not None else None
            update_data['updated_at'] = datetime.now(timezone.utc)
            updated_count: int = query.update(update_data, synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Updated {updated_count} snapshots successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error updating snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error updating snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        """Update multiple snapshots with different data"""
        raise NotImplementedError("Update multiple snapshots is not implemented")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        """Delete snapshots based on filters (hard delete)"""
        try:
            session: Session = self._get_session()
            query: Query = session.query(ContainerSnapshot)
            # Apply filters
            for key, value in filters.items():
                if hasattr(ContainerSnapshot, key) and value is not None:
                    converted_value = self._convert_filter_value(key, value)
                    query = query.filter(getattr(ContainerSnapshot, key) == converted_value)
            deleted_count: int = query.delete(synchronize_session=False)
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Deleted {deleted_count} snapshots successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        """Delete multiple snapshots with different filters (hard delete)"""
        try:
            session: Session = self._get_session()
            deleted_count: int = 0
            for filters in filter_list:
                query: Query = session.query(ContainerSnapshot)
                for key, value in filters.items():
                    if hasattr(ContainerSnapshot, key) and value is not None:
                        converted_value = self._convert_filter_value(key, value)
                        query = query.filter(getattr(ContainerSnapshot, key) == converted_value)
                count: int = query.delete(synchronize_session=False)
                deleted_count += count
            commit_result: OperationResult = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(
                success=True,
                message=f"Deleted {deleted_count} snapshots successfully"
            )
        except ValueError as e:
            logger.error(f"Value Error deleting multiple snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error deleting multiple snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple snapshots: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")
