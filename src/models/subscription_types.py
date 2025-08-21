"""
SubscriptionType model - Schema definition only
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, Index, DECIMAL, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# local
from src.models import Base


class Currency(enum.Enum):
    """Currency enum"""
    INR = "INR"
    USD = "USD"
    EUR = "EUR"


class SubscriptionType(Base):
    """
    SubscriptionType model representing subscription plans
    """
    __tablename__ = "subscription_types"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Plan information
    name = Column(String(100), nullable=False)  # Display name
    type = Column(String(50), unique=True, nullable=False)  # Internal type identifier
    amount = Column(DECIMAL(10, 2), nullable=False)  # Price
    currency = Column(Enum(Currency), nullable=False, default=Currency.INR)  # Currency code
    duration_days = Column(Integer, nullable=False)  # Subscription duration

    # Limits
    max_containers = Column(Integer, nullable=False, default=1)
    cpu_limit_per_container = Column(String(20), nullable=False, default="1")  # e.g., "1.0"
    memory_limit_per_container = Column(String(20), nullable=False, default="1GB")  # e.g., "1GB"

    # Description and status
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="subscription_type")
    orders = relationship("Orders", back_populates="subscription_type")

    # Indexes
    __table_args__ = (
        Index('idx_subscription_type_is_active', is_active),
        Index('idx_subscription_type_amount', amount),
        Index('idx_subscription_type_type', type),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "type": self.type,
            "amount": float(self.amount),
            "currency": self.currency.value if self.currency else None,
            "duration_days": self.duration_days,
            "max_containers": self.max_containers,
            "cpu_limit_per_container": self.cpu_limit_per_container,
            "memory_limit_per_container": self.memory_limit_per_container,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
