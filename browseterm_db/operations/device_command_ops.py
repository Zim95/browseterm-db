"""
DeviceCommand operations - Database operations for DeviceCommand model, plus the Part 1
transactional invariants (BROWSETERM_CLOUD_CONTROL_PLANE_MIGRATION.md):

  - Atomically activate one device and deactivate all others owned by the same user.
  - Transactionally reserve device quota and create a command.
  - Transactionally release quota exactly once.
  - Conditionally update a container only when device ID and placement generation match.
  - Prevent more than one active lifecycle command per container.
  - Reject commands assigned to inactive/wrong devices.

The plain CRUD methods (find/find_one/insert/update/delete) follow this repo's existing
one-session-per-call convention (see container_ops.py/device_ops.py) for consistency with every
other Ops class. The invariant methods below deliberately do NOT follow that convention - each one
opens exactly one session and commits (or rolls back) the whole multi-statement operation as a
single transaction, because their entire purpose is to make multi-step read-then-write sequences
atomic under concurrent callers. Splitting any of them across multiple sessions/commits would
reintroduce the exact race they exist to close.
"""
# builtins
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

# sqlalchemy
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Query, Session

# local
from browseterm_db.models.containers import Container
from browseterm_db.models.devices import Device, DeviceStatus
from browseterm_db.models.device_commands import ACTIVE_COMMAND_STATUSES, CommandOperation, CommandStatus, DeviceCommand
from browseterm_db.models.users import User
from browseterm_db.operations import DBOperations, OperationResult


logger = logging.getLogger(__name__)

# Only CREATE/RESUME commands hold runtime quota while in flight (Part 1: "Transactionally
# reserve device quota and create a command" - DELETE/HIBERNATE release capacity, they don't
# consume it up front).
_QUOTA_RESERVING_OPERATIONS = (CommandOperation.CREATE, CommandOperation.RESUME)


class DeviceCommandOps(DBOperations):
    """
    DeviceCommand operations implementing DBOperations abstract class, plus atomic invariants.
    """

    # ---- plain CRUD (DBOperations abstract methods) -------------------------------------------

    def _convert_filter_value(self, key: str, value: Any) -> Any:
        filter_conversion_map: dict = {
            'user_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v,
            'device_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v,
            'container_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v,
            'operation': lambda v: v if isinstance(v, CommandOperation) else CommandOperation(v),
            'status': lambda v: v if isinstance(v, CommandStatus) else CommandStatus(v),
        }
        if key in filter_conversion_map:
            return filter_conversion_map[key](value)
        return value

    def _convert_update_value(self, key: str, value: Any) -> Any:
        _parse_datetime = lambda v: datetime.fromisoformat(v) if isinstance(v, str) else v
        update_conversion_map: dict = {
            'status': lambda v: v if isinstance(v, CommandStatus) else CommandStatus(v),
            'delivered_at': _parse_datetime,
            'accepted_at': _parse_datetime,
            'started_at': _parse_datetime,
            'completed_at': _parse_datetime,
            'quota_released_at': _parse_datetime,
        }
        if key in update_conversion_map:
            return update_conversion_map[key](value)
        return value

    def _convert_insert_value(self, key: str, value: Any) -> Any:
        insert_conversion_map: dict = {
            'user_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v,
            'device_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v,
            'container_id': lambda v: uuid.UUID(v) if isinstance(v, str) else v,
            'operation': lambda v: v if isinstance(v, CommandOperation) else CommandOperation(v),
            'status': lambda v: v if isinstance(v, CommandStatus) else CommandStatus(v),
        }
        if key in insert_conversion_map:
            return insert_conversion_map[key](value)
        return value

    def find(self, filters: Dict[str, Any], limit: Optional[int] = None,
             offset: Optional[int] = None) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCommand)
            for key, value in filters.items():
                if hasattr(DeviceCommand, key) and value is not None:
                    query = query.filter(getattr(DeviceCommand, key) == self._convert_filter_value(key, value))
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            commands: List[DeviceCommand] = query.all()
            result_list = [c.to_dict() for c in commands]
            self._close_session()
            return OperationResult(success=True, message=f"Found {len(result_list)} commands", data=result_list)
        except ValueError as e:
            logger.error(f"Value Error finding commands: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding commands: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_one(self, filters: Dict[str, Any]) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCommand)
            for key, value in filters.items():
                if hasattr(DeviceCommand, key) and value is not None:
                    query = query.filter(getattr(DeviceCommand, key) == self._convert_filter_value(key, value))
            command: DeviceCommand = query.first()
            result_data = command.to_dict() if command else None
            message = "Command found" if command else "Command not found"
            self._close_session()
            return OperationResult(success=True, message=message, data=result_data)
        except ValueError as e:
            logger.error(f"Value Error finding command: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error finding command: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def find_pending_for_device(self, device_id: str) -> OperationResult:
        """QUEUED or DELIVERED commands for a device whose available_at has passed - what a
        reconnecting/polling Device Agent should be (re)sent. Duplicate delivery is expected and
        safe (Part 6)."""
        try:
            session: Session = self._get_session()
            now = datetime.now(timezone.utc)
            query: Query = session.query(DeviceCommand).filter(
                DeviceCommand.device_id == self._convert_filter_value('device_id', device_id),
                DeviceCommand.status.in_([CommandStatus.QUEUED, CommandStatus.DELIVERED, CommandStatus.ACCEPTED, CommandStatus.RUNNING]),
                DeviceCommand.available_at <= now,
            ).order_by(DeviceCommand.created_at.asc())
            commands: List[DeviceCommand] = query.all()
            result_list = [c.to_dict() for c in commands]
            self._close_session()
            return OperationResult(success=True, message=f"Found {len(result_list)} pending commands", data=result_list)
        except SQLAlchemyError as e:
            logger.error(f"Error finding pending commands: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert(self, data: Dict[str, Any]) -> OperationResult:
        """Direct insert, bypassing quota reservation - only for commands that never hold quota
        (DELETE, HIBERNATE, RECONCILE). CREATE/RESUME must go through
        reserve_quota_and_create_command instead so quota and command creation stay atomic."""
        try:
            operation = self._convert_insert_value('operation', data.get('operation'))
            if operation in _QUOTA_RESERVING_OPERATIONS:
                return OperationResult(
                    success=False,
                    error=f"{operation.value} commands must be created via reserve_quota_and_create_command",
                )
            session: Session = self._get_session()
            command = DeviceCommand(
                user_id=self._convert_insert_value('user_id', data.get('user_id')),
                device_id=self._convert_insert_value('device_id', data.get('device_id')),
                container_id=self._convert_insert_value('container_id', data.get('container_id')),
                operation=operation,
                placement_generation=data.get('placement_generation', 0),
                expected_container_state=data.get('expected_container_state'),
                status=self._convert_insert_value('status', data.get('status', CommandStatus.QUEUED)),
                request_id=data.get('request_id'),
                correlation_id=data.get('correlation_id'),
                container_config_json=data.get('container_config_json'),
            )
            session.add(command)
            session.flush()
            result_data = command.to_dict()
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message="Command created successfully", data=result_data)
        except ValueError as e:
            logger.error(f"Value Error creating command: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except IntegrityError as e:
            logger.error(f"Integrity error creating command: {str(e)}")
            self._rollback_and_close()
            return OperationResult(
                success=False,
                error="An active lifecycle command already exists for this container, or device/container/user not found",
            )
        except SQLAlchemyError as e:
            logger.error(f"Error creating command: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def insert_many(self, data_list: List[Dict[str, Any]]) -> OperationResult:
        raise NotImplementedError("Inserting multiple commands is not implemented")

    def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCommand)
            for key, value in filters.items():
                if hasattr(DeviceCommand, key) and value is not None:
                    query = query.filter(getattr(DeviceCommand, key) == self._convert_filter_value(key, value))
            update_data: Dict[str, Any] = {}
            for key, value in data.items():
                if hasattr(DeviceCommand, key) and key not in ['id', 'created_at', 'user_id', 'device_id']:
                    update_data[key] = self._convert_update_value(key, value) if value is not None else None
            update_data['updated_at'] = datetime.now(timezone.utc)
            updated_count: int = query.update(update_data, synchronize_session=False)
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message=f"Updated {updated_count} commands successfully")
        except ValueError as e:
            logger.error(f"Value Error updating commands: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error updating commands: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def update_many(self, updates: List[Dict[str, Any]]) -> OperationResult:
        raise NotImplementedError("Update multiple commands is not implemented")

    def delete(self, filters: Dict[str, Any]) -> OperationResult:
        try:
            session: Session = self._get_session()
            query: Query = session.query(DeviceCommand)
            for key, value in filters.items():
                if hasattr(DeviceCommand, key) and value is not None:
                    query = query.filter(getattr(DeviceCommand, key) == self._convert_filter_value(key, value))
            deleted_count: int = query.delete(synchronize_session=False)
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message=f"Deleted {deleted_count} commands successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting commands: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    def delete_many(self, filter_list: List[Dict[str, Any]]) -> OperationResult:
        try:
            session: Session = self._get_session()
            deleted_count = 0
            for filters in filter_list:
                query: Query = session.query(DeviceCommand)
                for key, value in filters.items():
                    if hasattr(DeviceCommand, key) and value is not None:
                        query = query.filter(getattr(DeviceCommand, key) == self._convert_filter_value(key, value))
                deleted_count += query.delete(synchronize_session=False)
            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message=f"Deleted {deleted_count} commands successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting multiple commands: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=f"Database error: {str(e)}")

    # ---- Part 1 transactional invariants -------------------------------------------------------

    def activate_device(self, user_id: str, device_id: str) -> OperationResult:
        """
        Atomically activate one device and deactivate all others owned by the same user.

        A single UPDATE of users.active_device_id IS the entire invariant: Postgres serializes
        concurrent UPDATEs of the same row, so two simultaneous activation requests for the same
        user can never both "win" - exactly one commits last and that is the final, and only,
        active device. This replaces the old find-then-loop-update pattern (still present in
        src/cloud/device_handlers.py's `_demote_other_devices`, not touched by this migration
        part) which does a separate SELECT and N separate UPDATEs across N+1 round trips - a
        window in which two racing requests can each demote the other and both end up "active".

        Fails (without changing anything) if the device does not exist or does not belong to this
        user - ownership is checked in the same statement via the WHERE clause on devices, not as
        a separate pre-check that could race with a concurrent revoke/reassignment.
        """
        session: Session = self._get_session()
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            device_uuid = uuid.UUID(device_id) if isinstance(device_id, str) else device_id

            owned = session.query(Device.id).filter(
                Device.id == device_uuid, Device.user_id == user_uuid, Device.revoked_at.is_(None),
            ).first()
            if not owned:
                self._rollback_and_close()
                return OperationResult(success=False, error="Device not found for this user")

            updated_count = session.query(User).filter(User.id == user_uuid).update(
                {"active_device_id": device_uuid, "updated_at": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
            if updated_count == 0:
                self._rollback_and_close()
                return OperationResult(success=False, error="User not found")

            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message="Device activated", data={"active_device_id": str(device_uuid)})
        except (ValueError, SQLAlchemyError) as e:
            logger.error(f"Error activating device: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))

    def reserve_quota_and_create_command(
        self,
        user_id: str,
        device_id: str,
        container_id: Optional[str],
        operation: CommandOperation,
        cpu: int,
        memory_bytes: int,
        storage_bytes: int,
        expected_container_state: Optional[str] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        container_config_json: Optional[str] = None,
    ) -> OperationResult:
        """
        Transactionally reserve device quota and create a command (CREATE/RESUME only).

        One session, one transaction:
          1. Lock the device row (SELECT ... FOR UPDATE) so two concurrent reservations against
             the same device cannot both read the same "available" snapshot and overcommit it -
             this is what "transactionally reserve" means; checking then updating in separate
             statements/sessions would have the exact same race `_demote_other_devices` has.
          2. Reject if the device is not this user's current active_device_id, or the device is
             REVOKED - "Reject commands assigned to inactive/wrong devices."
          3. Reject if allocated - reserved - used < requested (insufficient quota).
          4. Bump reserved_* on the device and insert the command in the same transaction.

        The partial unique index on device_commands (container_id, status IN active-statuses)
        enforces "only one active lifecycle command per container" at the database level - a
        second concurrent reservation for the same container fails with IntegrityError here,
        which is translated into a clean OperationResult failure below.
        """
        if operation not in _QUOTA_RESERVING_OPERATIONS:
            return OperationResult(success=False, error=f"{operation.value} does not reserve quota")

        session: Session = self._get_session()
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            device_uuid = uuid.UUID(device_id) if isinstance(device_id, str) else device_id
            container_uuid = uuid.UUID(container_id) if isinstance(container_id, str) else container_id

            user_row = session.query(User).filter(User.id == user_uuid).with_for_update().first()
            if not user_row:
                self._rollback_and_close()
                return OperationResult(success=False, error="User not found")
            if user_row.active_device_id != device_uuid:
                self._rollback_and_close()
                return OperationResult(success=False, error="Device is not the active device for this user")

            device_row = session.query(Device).filter(Device.id == device_uuid).with_for_update().first()
            if not device_row:
                self._rollback_and_close()
                return OperationResult(success=False, error="Device not found")
            if device_row.status != DeviceStatus.ACTIVE or device_row.revoked_at is not None:
                self._rollback_and_close()
                return OperationResult(success=False, error="Device is not online/active")

            available_cpu = device_row.allocated_cpu - device_row.reserved_cpu - device_row.used_cpu
            available_memory = device_row.allocated_memory_bytes - device_row.reserved_memory_bytes - device_row.used_memory_bytes
            available_storage = device_row.allocated_storage_bytes - device_row.reserved_storage_bytes - device_row.used_storage_bytes
            if cpu > available_cpu or memory_bytes > available_memory or storage_bytes > available_storage:
                self._rollback_and_close()
                return OperationResult(success=False, error="Insufficient device quota")

            placement_generation = 0
            if container_uuid is not None:
                container_row = session.query(Container).filter(Container.id == container_uuid).with_for_update().first()
                if not container_row:
                    self._rollback_and_close()
                    return OperationResult(success=False, error="Container not found")
                placement_generation = container_row.placement_generation + 1
                container_row.placement_generation = placement_generation
                container_row.device_id = device_uuid
                container_row.updated_at = datetime.now(timezone.utc)

            device_row.reserved_cpu += cpu
            device_row.reserved_memory_bytes += memory_bytes
            device_row.reserved_storage_bytes += storage_bytes
            device_row.updated_at = datetime.now(timezone.utc)

            command = DeviceCommand(
                user_id=user_uuid,
                device_id=device_uuid,
                container_id=container_uuid,
                operation=operation,
                placement_generation=placement_generation,
                expected_container_state=expected_container_state,
                status=CommandStatus.QUEUED,
                request_id=request_id,
                correlation_id=correlation_id,
                quota_reserved_cpu=cpu,
                quota_reserved_memory_bytes=memory_bytes,
                quota_reserved_storage_bytes=storage_bytes,
                container_config_json=container_config_json,
            )
            session.add(command)
            session.flush()
            result_data = command.to_dict()

            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message="Command created and quota reserved", data=result_data)
        except IntegrityError as e:
            logger.error(f"Integrity error reserving quota/creating command: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error="An active lifecycle command already exists for this container")
        except (ValueError, SQLAlchemyError) as e:
            logger.error(f"Error reserving quota/creating command: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))

    def release_quota_for_command(self, command_id: str) -> OperationResult:
        """
        Transactionally release quota exactly once.

        Guarded by quota_released_at: the UPDATE that decrements the device's reserved_* columns
        and the UPDATE that stamps quota_released_at happen in the same transaction as the SELECT
        ... FOR UPDATE that checked it was still NULL, so two concurrent release calls for the
        same command (e.g. a duplicate DELETE result and a reconciler both trying to release)
        cannot both decrement - the second one finds quota_released_at already set and no-ops.
        """
        session: Session = self._get_session()
        try:
            command_uuid = uuid.UUID(command_id) if isinstance(command_id, str) else command_id
            command_row = session.query(DeviceCommand).filter(DeviceCommand.id == command_uuid).with_for_update().first()
            if not command_row:
                self._rollback_and_close()
                return OperationResult(success=False, error="Command not found")
            if command_row.quota_released_at is not None:
                self._rollback_and_close()
                return OperationResult(success=True, message="Quota already released (no-op)", data={"already_released": True})
            if command_row.quota_reserved_cpu is None:
                self._rollback_and_close()
                return OperationResult(success=True, message="Command never reserved quota (no-op)", data={"already_released": True})

            device_row = session.query(Device).filter(Device.id == command_row.device_id).with_for_update().first()
            if device_row:
                device_row.reserved_cpu = max(0, device_row.reserved_cpu - (command_row.quota_reserved_cpu or 0))
                device_row.reserved_memory_bytes = max(0, device_row.reserved_memory_bytes - (command_row.quota_reserved_memory_bytes or 0))
                device_row.reserved_storage_bytes = max(0, device_row.reserved_storage_bytes - (command_row.quota_reserved_storage_bytes or 0))
                device_row.updated_at = datetime.now(timezone.utc)

            command_row.quota_released_at = datetime.now(timezone.utc)
            command_row.updated_at = datetime.now(timezone.utc)

            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message="Quota released", data={"already_released": False})
        except (ValueError, SQLAlchemyError) as e:
            logger.error(f"Error releasing quota: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))

    def conditional_container_update(
        self, container_id: str, expected_device_id: str, expected_placement_generation: int, update_data: Dict[str, Any],
    ) -> OperationResult:
        """
        Conditionally update a container only when device ID and placement generation match.

        A single UPDATE ... WHERE id = :id AND device_id = :device_id AND placement_generation =
        :generation is the whole invariant - if a newer command/activation has already moved this
        container to a different device or bumped its generation, the WHERE clause matches zero
        rows and this is a safe no-op (data["matched"] == 0), never a silent overwrite of a newer
        placement with a stale one (Part 14: "Old placement updates are rejected using placement
        generation").
        """
        session: Session = self._get_session()
        try:
            container_uuid = uuid.UUID(container_id) if isinstance(container_id, str) else container_id
            device_uuid = uuid.UUID(expected_device_id) if isinstance(expected_device_id, str) else expected_device_id

            safe_data = {k: v for k, v in update_data.items() if hasattr(Container, k) and k not in ('id', 'created_at', 'user_id')}
            if 'status' in safe_data and isinstance(safe_data['status'], str):
                from browseterm_db.models.containers import ContainerStatus
                safe_data['status'] = ContainerStatus(safe_data['status'])
            safe_data['updated_at'] = datetime.now(timezone.utc)

            matched = session.query(Container).filter(
                and_(
                    Container.id == container_uuid,
                    Container.device_id == device_uuid,
                    Container.placement_generation == expected_placement_generation,
                )
            ).update(safe_data, synchronize_session=False)

            commit_result = self._commit_and_close()
            if not commit_result.success:
                return commit_result
            return OperationResult(success=True, message=f"Matched {matched} container(s)", data={"matched": matched})
        except (ValueError, SQLAlchemyError) as e:
            logger.error(f"Error conditionally updating container: {str(e)}")
            self._rollback_and_close()
            return OperationResult(success=False, error=str(e))
