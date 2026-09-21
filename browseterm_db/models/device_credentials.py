"""
DeviceCredential model - Schema definition only

Migration Part 1: durable, revocable record of a device's credential. This table is the
authoritative audit trail (created/last-used/rotated/revoked); today's actual token *validation*
still happens against Redis (src/authentication/device_token_manager.py, browseterm-server) -
wiring token issuance/validation to write through to this table is Part 4 (device-linking
authentication) work, not done here. Never store the raw token - only its hash and a short
non-secret prefix/id used to look the row up quickly.
"""
# builtins
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# sqlalchemy
from sqlalchemy import Column, String, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# local
from browseterm_db.models import Base


class DeviceCredential(Base):
    """
    DeviceCredential model representing one issued (or rotated/revoked) device credential.
    """
    __tablename__ = "device_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    device_id = Column(UUID(as_uuid=True), ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)

    # Short, non-secret prefix of the raw token (e.g. "bst_device_" + first few chars) used for
    # fast lookup without scanning every row's hash. Never sufficient on its own to authenticate.
    token_prefix = Column(String(32), nullable=False, index=True)
    # Argon2id (or equivalent) hash of the raw token. The raw token itself is returned to the
    # caller exactly once, at issuance, and is never persisted anywhere in this table.
    token_hash = Column(String(255), nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    rotated_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    device = relationship("Device")

    __table_args__ = (
        Index('idx_device_credential_device_id', device_id),
        Index('idx_device_credential_token_prefix', token_prefix),
        Index('idx_device_credential_revoked_at', revoked_at),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary. Never includes token_hash."""
        return {
            "id": str(self.id),
            "device_id": str(self.device_id),
            "token_prefix": self.token_prefix,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "rotated_at": self.rotated_at.isoformat() if self.rotated_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
