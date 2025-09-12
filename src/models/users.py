"""
User model - Schema definition only
"""
# builtins
import enum
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, DateTime, Boolean, Index, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# local
from src.models import Base


class AuthProvider(enum.Enum):
    """Authentication provider enum"""
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    """
    User model representing application users
    """
    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User information
    email = Column(String(255), unique=True, nullable=False, index=True)
    provider = Column(Enum(AuthProvider), nullable=False)

    '''
    Why do I need the provider_id?
    1. If user changes their email within the same provider (eg google), we will still be able to identify the user.
    2. Different people use a shared email but with different providers (eg google and github), then they need to be treated as different accounts.

    Basically, we use provider and provider_id to check if the user is unique or the same.
    '''
    provider_id = Column(String(255), nullable=False)

    # Timestamps
    '''
    Why do I need created_at?
    1. Answer questions like: how many users signed up this month? User growth over time?
    2. Show welcome message to new users. Send follow up emails.
    3. Track account age: We can introduce age specific features like gifts, discounts, etc for long users.
    '''
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    '''
    Why do I need updated_at? (We update this field even if we change the smallest thing like last_login)
    1. Track when user last updated their account. Find inactive users, recently active users.
    2. Security: Alert when suspicious updates were made. Track when user updated profile.
    3. MOST IMPORTANT: Sync only modified records. Sync only records modified since last sync.
    '''
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    '''
    Why do I need last_login?
    1. Track when user last logged in. Send emails, or deactivate accounts if they haven't logged in for a long time.
    2. Only to be set when the user actually logs in, not during user creation.
    '''
    last_login = Column(DateTime, nullable=True)

    '''
    This is for soft delete. We don't want to delete the user, we just want to deactivate them.
    So, if we want to delete the user, we just set this field to False.
    We can resume the account by setting this field to True if the user ever wants to login again but has a deactivated account.
    '''
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    containers = relationship("Container", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = relationship("Orders", back_populates="user", cascade="all, delete-orphan")

    # Indexes and constraints
    '''
    Why do I need the UniqueConstraint on provider and provider_id?
    --------------------------------------------------------------
    - Well, provider_id will be unique for a particular provider.
    - But, we cannot guarantee uniqueness across providers. Eg: google and github can have the same provider_id by chance.
    - So, we create a composite key of provider and provider_id to ensure uniqueness across providers.
    '''
    __table_args__ = (
        Index('idx_user_provider', provider),
        Index('idx_user_is_active', is_active),
        Index('idx_user_email_provider', email, provider),
        UniqueConstraint('provider', 'provider_id', name='uq_user_provider_provider_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "provider": self.provider.value if self.provider else None,
            "provider_id": self.provider_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active
        }
