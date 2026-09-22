"""
DeviceCommand model - Schema definition only

Migration Part 1 (BROWSETERM_CLOUD_CONTROL_PLANE_MIGRATION.md): the durable command store.
`id` doubles as the idempotency key - a duplicate delivery/retry of the same command always
resolves to this same row, never a second one. PostgreSQL is authoritative here; Redis is
explicitly NOT the durable command store per the migration doc's fixed product decisions.
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, Integer, DateTime, Index, ForeignKey, Enum, and_
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

# local
from browseterm_db.models import Base


class CommandOperation(enum.Enum):
    """Device command operation enum."""
    CREATE = "Create"
    DELETE = "Delete"
    HIBERNATE = "Hibernate"
    RESUME = "Resume"
    RECONCILE = "Reconcile"  # later reconciliation operations, per the migration doc's Part 1 spec
    SAVE = "Save"  # snapshot without deleting the pod (unlike HIBERNATE) - core reliability feature


class CommandStatus(enum.Enum):
    """Device command lifecycle status enum."""
    QUEUED = "Queued"
    DELIVERED = "Delivered"
    ACCEPTED = "Accepted"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


# Statuses that count as "an active lifecycle command exists for this container" - enforced by a
# partial unique index (see the Part 1 migration) so at most one of these can exist per container
# at a time. Kept here, not just in the migration, so DeviceCommandOps and the migration can never
# drift apart on what "active" means.
ACTIVE_COMMAND_STATUSES = (CommandStatus.QUEUED, CommandStatus.DELIVERED, CommandStatus.ACCEPTED, CommandStatus.RUNNING)


class DeviceCommand(Base):
    """
    DeviceCommand model representing one durable command dispatched to a Device Agent.
    """
    __tablename__ = "device_commands"

    # Primary key - also the idempotency key used by Device Agent to deduplicate delivery.
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    # Nullable only for device-wide commands (e.g. a future device-level reconcile/drain); every
    # CREATE/DELETE/HIBERNATE/RESUME command today always has one.
    container_id = Column(UUID(as_uuid=True), ForeignKey('containers.id', ondelete='CASCADE'), nullable=True)

    operation = Column(Enum(CommandOperation), nullable=False)

    # The placement_generation this command was created against (copied from containers.
    # placement_generation at creation time) and, for CREATE/RESUME, the generation the command
    # is establishing. Device Agent's own conditional container update must match this, not
    # whatever containers.placement_generation happens to read as by the time the result arrives.
    placement_generation = Column(Integer, nullable=False, default=0)
    # Free-text/enum-value snapshot of the container status this command expects to find/leave -
    # a documented string, not a foreign type, since it is a point-in-time expectation, not a
    # live reference (matches container_snapshots' own deliberate use of plain strings elsewhere).
    expected_container_state = Column(String(20), nullable=True)

    # Migration Parts 8-11: the canonical container config snapshot Cloud resolved at
    # command-creation time (image name, resource requests/limits, env vars, publish info,
    # saved_image for Resume) - embedded verbatim into ExecuteCommand.container_config_json on
    # delivery (see browseterm-server's src/control/servicer.py). JSON text, not a JSON column
    # type, since it crosses the wire as an opaque string on the protobuf side too.
    container_config_json = Column(String(4000), nullable=True)

    status = Column(Enum(CommandStatus), nullable=False, default=CommandStatus.QUEUED)
    attempt_count = Column(Integer, nullable=False, default=0)

    # Delivery/redelivery scheduling - a command is only eligible for (re)delivery once
    # available_at <= now(). Lets a retry backoff without a separate scheduler table.
    available_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    delivered_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    progress_stage = Column(String(50), nullable=True)
    progress_message = Column(String(500), nullable=True)  # bounded - never raw stack traces/logs

    result = Column(JSON, nullable=True)  # documented schema per operation type, set on completion

    error_code = Column(String(100), nullable=True)
    error_message = Column(String(1000), nullable=True)  # bounded and sanitized, never raw secrets

    request_id = Column(String(64), nullable=True)  # correlates back to the originating browser request
    correlation_id = Column(String(64), nullable=True)  # correlates across Cloud/Agent/Container Maker logs

    # Quota accounting - exactly-once release guard (see DeviceCommandOps.release_quota_for_command).
    # Nullable: only CREATE/RESUME commands ever reserve quota in the first place.
    quota_reserved_cpu = Column(Integer, nullable=True)
    quota_reserved_memory_bytes = Column(Integer, nullable=True)
    quota_reserved_storage_bytes = Column(Integer, nullable=True)
    quota_released_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    device = relationship("Device")
    container = relationship("Container")

    __table_args__ = (
        Index('idx_device_command_device_status_available', device_id, status, available_at),
        Index('idx_device_command_container_id', container_id),
        Index('idx_device_command_status_updated_at', status, updated_at),
        Index('idx_device_command_user_id', user_id),
        # "Prevent more than one active lifecycle command per container" (Part 1) - a partial
        # unique index, not a Python-level check, so it holds even under concurrent writers from
        # separate sessions/processes. MUST be declared here (not only emitted via a hand-written
        # migration's op.execute) so Alembic's autogenerate reproduces it too - this repo's own
        # test convention (AAA_InitialSetup in every tests/test_*_ops.py file) builds the test
        # schema by autogenerating straight from these models, not by replaying versions/*.py.
        Index(
            'uq_device_commands_one_active_per_container',
            container_id,
            unique=True,
            postgresql_where=and_(container_id.isnot(None), status.in_(list(ACTIVE_COMMAND_STATUSES))),
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "device_id": str(self.device_id),
            "container_id": str(self.container_id) if self.container_id else None,
            "operation": self.operation.value if self.operation else None,
            "placement_generation": self.placement_generation,
            "expected_container_state": self.expected_container_state,
            "container_config_json": self.container_config_json,
            "status": self.status.value if self.status else None,
            "attempt_count": self.attempt_count,
            "available_at": self.available_at.isoformat() if self.available_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress_stage": self.progress_stage,
            "progress_message": self.progress_message,
            "result": self.result,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "quota_reserved_cpu": self.quota_reserved_cpu,
            "quota_reserved_memory_bytes": self.quota_reserved_memory_bytes,
            "quota_reserved_storage_bytes": self.quota_reserved_storage_bytes,
            "quota_released_at": self.quota_released_at.isoformat() if self.quota_released_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
