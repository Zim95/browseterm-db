"""
Image model - Schema definition only
"""
# builtins
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, DateTime, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# local
from browseterm_db.models import Base


class Image(Base):
    """
    Image model representing container images
    """
    __tablename__ = "images"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Image information
    name = Column(String(255), nullable=False, unique=True, index=True)
    image = Column(String(500), nullable=False)

    # Soft delete flag
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    containers = relationship("Container", back_populates="image_ref")

    # Indexes
    __table_args__ = (
        Index('idx_image_is_active', is_active),
        Index('idx_image_name', name),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "image": self.image,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
