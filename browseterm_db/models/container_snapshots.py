"""
ContainerSnapshot model - Schema definition only

P15 (see ~/browseterm/p.md's "P15" section, plan section 5.4/5.5/5.6): one row per workspace
save/snapshot attempt. Deliberately a SEPARATE table from `images` (the base-image catalog) -
saved workspace images must never mix into that catalog.
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, Integer, DateTime, Index, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# local
from browseterm_db.models import Base


class SnapshotStatus(enum.Enum):
    """Snapshot attempt lifecycle status."""
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


class ContainerSnapshot(Base):
    """
    One row per workspace save/snapshot attempt.

    `(container_id, request_id)` is unique so a retried request for the same attempt reuses the
    existing row instead of allocating a new version (plan section 5.5's idempotency algorithm).
    `(container_id, version_sequence)` is unique so `containers.next_snapshot_sequence` (the
    atomic counter allocating `version_sequence`) can never produce two rows with the same
    sequence for one container.
    """
    __tablename__ = "container_snapshots"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key. ON DELETE CASCADE: a snapshot row has no meaning without its container, and
    # ContainerOps.delete() does a bulk `query.delete()` that bypasses SQLAlchemy ORM-level
    # cascades entirely (those only fire on session.delete() of an individually loaded object) -
    # this has to be a real DB-level cascade or deleting a container with snapshot history would
    # raise a FK violation.
    container_id = Column(UUID(as_uuid=True), ForeignKey('containers.id', ondelete='CASCADE'), nullable=False)

    # Version allocation - see containers.next_snapshot_sequence (plan section 5.5). version_sequence
    # is the raw integer allocated atomically; version is its 5-part dotted-decimal formatting
    # (plan section 5.6, e.g. 1 -> "0.0.0.0.1", 100 -> "0.0.1.0.0") - formatted and stored once at
    # allocation time, never recomputed via string arithmetic later.
    version_sequence = Column(Integer, nullable=False)
    version = Column(String(20), nullable=False)

    # Registry location of the built image, once known.
    image_repository = Column(String(500), nullable=False)
    image_reference = Column(String(500), nullable=True)
    registry_digest = Column(String(255), nullable=True)

    # The request_id that originated this attempt - see the class docstring's idempotency note.
    request_id = Column(String(64), nullable=False)

    status = Column(Enum(SnapshotStatus), nullable=False, default=SnapshotStatus.PENDING)
    error_detail = Column(String(1000), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    container = relationship("Container", back_populates="snapshots")

    # Indexes and constraints
    __table_args__ = (
        Index('idx_container_snapshot_container_id', container_id),
        Index('idx_container_snapshot_status', status),
        Index('idx_container_snapshot_created_at', created_at),
        UniqueConstraint('container_id', 'request_id', name='uq_container_snapshot_container_request'),
        UniqueConstraint('container_id', 'version_sequence', name='uq_container_snapshot_container_version'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "container_id": str(self.container_id),
            "version_sequence": self.version_sequence,
            "version": self.version,
            "image_repository": self.image_repository,
            "image_reference": self.image_reference,
            "registry_digest": self.registry_digest,
            "request_id": self.request_id,
            "status": self.status.value if self.status else None,
            "error_detail": self.error_detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
