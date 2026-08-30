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

    gpu_info = Column(JSON, nullable=True)  # Optional GPU discovery/allocation info as JSON

    # Status and lifecycle timestamps
    status = Column(Enum(DeviceStatus), nullable=False, default=DeviceStatus.ACTIVE)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime, nullable=True)  # updated by device heartbeat
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="devices")
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
            "total_cpu": self.total_cpu,
            "total_memory_bytes": self.total_memory_bytes,
            "total_storage_bytes": self.total_storage_bytes,
            "allocated_cpu": self.allocated_cpu,
            "allocated_memory_bytes": self.allocated_memory_bytes,
            "allocated_storage_bytes": self.allocated_storage_bytes,
            "used_cpu": self.used_cpu,
            "used_memory_bytes": self.used_memory_bytes,
            "used_storage_bytes": self.used_storage_bytes,
            "gpu_info": self.gpu_info,
            "status": self.status.value if self.status else None,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
