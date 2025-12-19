"""
Container model - Schema definition only
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, DateTime, Index, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

# local
from browseterm_db.models import Base


DEFAULT_CPU_LIMIT: str = '1'
DEFAULT_MEMORY_LIMIT: str = '1Gi'
DEFAULT_STORAGE_LIMIT: str = '2Gi'


class ContainerStatus(enum.Enum):
    """Container status enum - Kubernetes pod phases"""
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class Container(Base):
    """
    Container model representing user containers
    """
    __tablename__ = "containers"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey('images.id', ondelete='SET NULL'), nullable=True)

    # Container information
    name = Column(String(255), nullable=False)
    status = Column(Enum(ContainerStatus), nullable=False, default=ContainerStatus.PENDING)

    # Resource limits
    cpu_limit = Column(String(20), nullable=False, default='1')  # e.g., "1.0"
    memory_limit = Column(String(20), nullable=False, default='1Gi')  # e.g., "1GB"
    storage_limit = Column(String(20), nullable=False, default='2Gi')  # e.g., "2GB"

    # Configuration
    ip_address = Column(String(20), nullable=True)  # IP address of the container
    port_mappings = Column(JSON, nullable=True)  # Port configuration as JSON
    environment_vars = Column(JSON, nullable=True)  # Environment variables as JSON
    associated_resources = Column(JSON, nullable=True)  # Resources assigned to the container as JSON

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    '''
    Operational Fields:
    -------------------
    1. We need kubernetes_id because we first make an entry to the database and then get the kubernetes ID from the kubernetes API.
        This is to ensure better user experience.
    2. We need saved_image because, sometimes, our container might go down without the user knowing.
        We would need to restore the container from the saved image and update the kubernetes_id.
    '''
    kubernetes_id = Column(String(255), nullable=True)  # Kubernetes ID of the container
    saved_image = Column(String(20), nullable=True)  # Saved image - if you have a saved image, we use this image directly.

    # Relationships
    user = relationship("User", back_populates="containers")
    image_ref = relationship("Image", back_populates="containers")

    # Indexes and constraints
    __table_args__ = (
        Index('idx_container_user_id', user_id),
        Index('idx_container_image_id', image_id),
        Index('idx_container_status', status),
        Index('idx_container_user_status', user_id, status),
        Index('idx_container_deleted_at', deleted_at),
        UniqueConstraint('user_id', 'name', name='uq_container_user_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "image_id": str(self.image_id) if self.image_id else None,
            "name": self.name,
            "status": self.status.value if self.status else None,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "storage_limit": self.storage_limit,
            "ip_address": self.ip_address,
            "port_mappings": self.port_mappings,
            "environment_vars": self.environment_vars,
            "associated_resources": self.associated_resources,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "kubernetes_id": self.kubernetes_id,
            "saved_image": self.saved_image
        }
