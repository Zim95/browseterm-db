"""
Subscription model - Schema definition only
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, DateTime, Boolean, Index, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# local
from src.models import Base


class SubscriptionStatus(enum.Enum):
    """Subscription status enum"""
    ACTIVE = "Active"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"
    PENDING = "Pending"


class Subscription(Base):
    """
    Subscription model representing user subscriptions
    """
    __tablename__ = "subscriptions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True, nullable=False)
    subscription_type_id = Column(UUID(as_uuid=True), ForeignKey('subscription_types.id'), nullable=False)

    # Subscription status and details
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    auto_renew = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    valid_until = Column(DateTime, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscription", uselist=False)
    subscription_type = relationship("SubscriptionType", back_populates="subscriptions")
    orders = relationship("Orders", back_populates="subscription", cascade="all, delete-orphan")

    # Indexes and constraints
    __table_args__ = (
        Index('idx_subscription_user_id', user_id),
        Index('idx_subscription_status', status),
        Index('idx_subscription_type_id', subscription_type_id),
        Index('idx_subscription_valid_until', valid_until),
        Index('idx_subscription_auto_renew', auto_renew),
        UniqueConstraint('user_id', name='uq_subscription_user_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "subscription_type_id": str(self.subscription_type_id),
            "status": self.status.value if self.status else None,
            "auto_renew": self.auto_renew,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None
        }
