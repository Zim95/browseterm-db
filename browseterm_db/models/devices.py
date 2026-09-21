"""
Device model - Schema definition only
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Index, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

# local
from browseterm_db.models import Base


class DeviceStatus(enum.Enum):
    """Device lifecycle status enum"""
    ACTIVE = "Active"      # registered and usable
    INACTIVE = "Inactive"  # not currently heartbeating (has not been reconciled/marked revoked)
    REVOKED = "Revoked"    # explicitly revoked, no longer usable


class TunnelStatus(enum.Enum):
    """remotetunelling.md: a device's outbound tunnel (ngrok today) reachability state."""
    ONLINE = "Online"
    OFFLINE = "Offline"


class Device(Base):
    """
    Device model representing a Browseterm installation/device belonging to a user.

    Holds physical machine resources, Browseterm's allocation out of those resources,
    a fast cached view of what is currently in use, and heartbeat/runtime identity.

    `available_*` (allocated - used) is intentionally NOT persisted -- it is derived at
    read time by callers, since physical capacity, Browseterm's allocation and current
    usage are three distinct concepts that can each change independently.
    """
    __tablename__ = "devices"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Device identity
    device_name = Column(String(255), nullable=False)
    os = Column(String(50), nullable=False)
    architecture = Column(String(20), nullable=False)
    runtime_version = Column(String(50), nullable=True)
    agent_version = Column(String(50), nullable=True)  # Device Agent version reported in its Hello

    # Migration Part 14: a stable ID minted once per real Desktop/CLI process startup (not per
    # gRPC reconnect). A startup may request device activation exactly once using this ID; Cloud
    # treats a repeated activation request with the SAME startup_id as idempotent, and a transient
    # reconnect (which reuses the existing startup_id rather than minting a new one) must never
    # re-trigger activation. Nullable: no meaning until a Device Agent actually connects.
    startup_id = Column(String(100), nullable=True)

    # Migration Part 6/7: bumped by Cloud every time a NEW authenticated gRPC stream generation
    # for this device replaces the previous one. Lets Cloud/Device Agent detect and discard a
    # stale command-result or status report that arrived from a connection generation that has
    # already been superseded by a newer one (same shape as tunnel_generation below, applied to
    # the control stream instead of the terminal tunnel).
    connection_generation = Column(Integer, nullable=False, default=0)

    # Physical machine capacity
    total_cpu = Column(Integer, nullable=False)
    total_memory_bytes = Column(BigInteger, nullable=False)
    total_storage_bytes = Column(BigInteger, nullable=False)

    # Browseterm's allocation out of the physical capacity above
    allocated_cpu = Column(Integer, nullable=False)
    allocated_memory_bytes = Column(BigInteger, nullable=False)
    allocated_storage_bytes = Column(BigInteger, nullable=False)

    # Cached usage (fast counters -- reconciled against actual Kubernetes state elsewhere)
    used_cpu = Column(Integer, nullable=False, default=0)
    used_memory_bytes = Column(BigInteger, nullable=False, default=0)
    used_storage_bytes = Column(BigInteger, nullable=False, default=0)

    '''
    Migration Part 1: quota held by IN-FLIGHT device_commands (CREATE/RESUME) that have not yet
    completed, distinct from `used_*` (confirmed running workloads). A Create/Resume request must
    reserve quota before a command is even delivered, so two concurrent requests can't both
    observe "enough capacity" and overcommit the device; `used_*` alone can't do this because it
    is only updated by status_monitor after the pod is actually observed running, which is too
    late to prevent a race. See DeviceCommandOps.reserve_quota_and_create_command /
    release_quota_for_command for the only code paths allowed to change these.
    '''
    reserved_cpu = Column(Integer, nullable=False, default=0)
    reserved_memory_bytes = Column(BigInteger, nullable=False, default=0)
    reserved_storage_bytes = Column(BigInteger, nullable=False, default=0)

    gpu_info = Column(JSON, nullable=True)  # Optional GPU discovery/allocation info as JSON

    # Status and lifecycle timestamps
    status = Column(Enum(DeviceStatus), nullable=False, default=DeviceStatus.ACTIVE)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime, nullable=True)  # updated by device heartbeat
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    revoked_at = Column(DateTime, nullable=True)

    # remotetunelling.md: at most one live tunnel per device at a time - flat columns here rather
    # than a separate joined table, matching this project's existing convention of tracking a
    # device's own live/heartbeat state directly on `devices` (see last_seen_at above). tunnel_*
    # is intentionally ALL-nullable: a device that's never registered a tunnel has none of this,
    # not zero-valued placeholders.
    tunnel_provider = Column(String(50), nullable=True)
    tunnel_public_url = Column(String(2048), nullable=True)
    tunnel_status = Column(Enum(TunnelStatus), nullable=True)
    # Monotonically increasing per device, set by the registrar. Guards against a delayed request
    # from a dead/restarted registrar instance overwriting a newer tunnel - a write is only
    # accepted if its generation is >= the currently stored one.
    tunnel_generation = Column(Integer, nullable=False, default=0)
    tunnel_connected_at = Column(DateTime, nullable=True)
    tunnel_last_heartbeat_at = Column(DateTime, nullable=True)

    # Relationships. explicit foreign_keys: see users.py's own `devices` relationship docstring -
    # users.active_device_id is a second, unrelated FK path between these two tables.
    user = relationship("User", back_populates="devices", foreign_keys=[user_id])
    containers = relationship("Container", back_populates="device_ref")

    # Indexes and constraints
    __table_args__ = (
        Index('idx_device_user_id', user_id),
        Index('idx_device_last_seen_at', last_seen_at),
        Index('idx_device_status', status),
        UniqueConstraint('user_id', 'device_name', name='uq_device_user_device_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "device_name": self.device_name,
            "os": self.os,
            "architecture": self.architecture,
            "runtime_version": self.runtime_version,
            "agent_version": self.agent_version,
            "startup_id": self.startup_id,
            "connection_generation": self.connection_generation,
            "total_cpu": self.total_cpu,
            "total_memory_bytes": self.total_memory_bytes,
            "total_storage_bytes": self.total_storage_bytes,
            "allocated_cpu": self.allocated_cpu,
            "allocated_memory_bytes": self.allocated_memory_bytes,
            "allocated_storage_bytes": self.allocated_storage_bytes,
            "used_cpu": self.used_cpu,
            "used_memory_bytes": self.used_memory_bytes,
            "used_storage_bytes": self.used_storage_bytes,
            "reserved_cpu": self.reserved_cpu,
            "reserved_memory_bytes": self.reserved_memory_bytes,
            "reserved_storage_bytes": self.reserved_storage_bytes,
            "gpu_info": self.gpu_info,
            "status": self.status.value if self.status else None,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "tunnel_provider": self.tunnel_provider,
            "tunnel_public_url": self.tunnel_public_url,
            "tunnel_status": self.tunnel_status.value if self.tunnel_status else None,
            "tunnel_generation": self.tunnel_generation,
            "tunnel_connected_at": self.tunnel_connected_at.isoformat() if self.tunnel_connected_at else None,
            "tunnel_last_heartbeat_at": self.tunnel_last_heartbeat_at.isoformat() if self.tunnel_last_heartbeat_at else None,
        }
