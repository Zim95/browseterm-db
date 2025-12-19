"""
Orders model - Schema definition only
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, DateTime, Index, ForeignKey, DECIMAL, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# local
from browseterm_db.models import Base


class OrderStatus(enum.Enum):
    """Order status enum"""
    PENDING = "Pending"
    PAID = "Paid"
    FAILED = "Failed"
    REFUNDED = "Refunded"


class OrdersCurrency(enum.Enum):
    """Currency enum"""
    INR = "INR"
    USD = "USD"
    EUR = "EUR"


class Orders(Base):
    """
    Orders model representing payment orders
    """
    __tablename__ = "orders"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    '''
    Why is subscription_id nullable?
    --------------------------------
    - Because, we want to allow users to make orders without a subscription.
    - We can later update the order to add a subscription.
    - This is useful for one-time orders.
    - For example, a user can buy a container for a one-time fee.
    - We can later update the order to add a subscription.
    1. New user orders Basic Plan
        - subscription_type_id = "basic-plan"
        - subscription_id = NULL (no existing subscription)
    2. After payment, create new subscription record
        - Now user has subscription_id = "sub-123"
    3. User renews Basic Plan
        - subscription_type_id = "basic-plan" 
        - subscription_id = "sub-123" (renewing existing)
    4. User upgrades to Premium
        - subscription_type_id = "premium-plan"
        - subscription_id = "sub-123" (upgrading existing)
    '''
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.id'), nullable=True)
    subscription_type_id = Column(UUID(as_uuid=True), ForeignKey('subscription_types.id'), nullable=False)

    # Payment information
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(Enum(OrdersCurrency), nullable=False, default=OrdersCurrency.INR)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    payment_method = Column(String(100), nullable=True)  # stripe, paypal, etc.
    payment_provider_id = Column(String(255), nullable=True)  # External payment reference ID

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    subscription = relationship("Subscription", back_populates="orders")
    subscription_type = relationship("SubscriptionType", back_populates="orders")

    # Indexes
    __table_args__ = (
        Index('idx_orders_user_id', user_id),
        Index('idx_orders_subscription_id', subscription_id),
        Index('idx_orders_status', status),
        Index('idx_orders_created_at', created_at),
        Index('idx_orders_user_status', user_id, status),
        Index('idx_orders_payment_provider_id', payment_provider_id),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "subscription_id": str(self.subscription_id) if self.subscription_id else None,
            "subscription_type_id": str(self.subscription_type_id),
            "amount": f"{self.amount:.2f}",  # Format with 2 decimal places
            "currency": self.currency.value if self.currency else None,
            "status": self.status.value if self.status else None,
            "payment_method": self.payment_method,
            "payment_provider_id": self.payment_provider_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None
        }
