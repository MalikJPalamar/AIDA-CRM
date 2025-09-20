"""
AIDA-CRM Communication Models
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from ..core.database import Base


class CommunicationType(str, Enum):
    """Communication type enumeration"""
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    MEETING = "meeting"
    NOTE = "note"


class CommunicationDirection(str, Enum):
    """Communication direction enumeration"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CommunicationStatus(str, Enum):
    """Communication status enumeration"""
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    FAILED = "failed"


class Communication(Base):
    """Communication model for tracking interactions"""
    __tablename__ = "communications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"))
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"))
    type = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    subject = Column(String(200))
    content = Column(Text)
    status = Column(String(20), default=CommunicationStatus.SENT.value)
    sent_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    sent_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    clicked_at = Column(DateTime(timezone=True))
    replied_at = Column(DateTime(timezone=True))
    metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="communications")
    deal = relationship("Deal", back_populates="communications")
    sender = relationship("User", backref="sent_communications")

    @property
    def is_outbound(self) -> bool:
        """Check if communication is outbound"""
        return self.direction == CommunicationDirection.OUTBOUND.value

    @property
    def is_opened(self) -> bool:
        """Check if communication was opened"""
        return self.opened_at is not None

    @property
    def is_replied(self) -> bool:
        """Check if communication was replied to"""
        return self.replied_at is not None

    def __repr__(self):
        return f"<Communication(type='{self.type}', direction='{self.direction}', status='{self.status}')>"