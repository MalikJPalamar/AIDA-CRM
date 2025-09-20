"""
AIDA-CRM Event Models
"""

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from enum import Enum

from ..core.database import Base


class EventStatus(str, Enum):
    """Event processing status"""
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class Event(Base):
    """Event model for NATS integration and audit trail"""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    data = Column(JSONB, nullable=False)
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    status = Column(String(20), default=EventStatus.PENDING.value, index=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)

    @property
    def is_processed(self) -> bool:
        """Check if event is processed"""
        return self.status == EventStatus.PROCESSED.value

    @property
    def is_failed(self) -> bool:
        """Check if event failed"""
        return self.status == EventStatus.FAILED.value

    @property
    def can_retry(self) -> bool:
        """Check if event can be retried"""
        return self.is_failed and self.retry_count < 3

    def __repr__(self):
        return f"<Event(type='{self.event_type}', subject='{self.subject}', status='{self.status}')>"