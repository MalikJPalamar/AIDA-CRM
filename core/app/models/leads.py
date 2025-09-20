"""
AIDA-CRM Lead Models
"""

from sqlalchemy import Column, String, Numeric, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from ..core.database import Base


class LeadStatus(str, Enum):
    """Lead status enumeration"""
    NEW = "new"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"


class Lead(Base):
    """Lead model for capturing potential customers"""
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(200))
    phone = Column(String(20))
    source = Column(String(50), default="web")
    campaign = Column(String(100))
    utm_params = Column(JSONB)
    custom_fields = Column(JSONB)
    qualification_score = Column(
        Numeric(3, 2),
        CheckConstraint('qualification_score >= 0 AND qualification_score <= 1')
    )
    status = Column(String(20), default=LeadStatus.NEW.value)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    ip_address = Column(INET)
    user_agent = Column(Text)
    referer = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    assigned_user = relationship("User", backref="assigned_leads")
    deals = relationship("Deal", back_populates="lead")
    communications = relationship("Communication", back_populates="lead")

    @property
    def full_name(self) -> str:
        """Get lead's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    @property
    def is_qualified(self) -> bool:
        """Check if lead is qualified"""
        return self.status == LeadStatus.QUALIFIED.value

    def __repr__(self):
        return f"<Lead(email='{self.email}', status='{self.status}', score={self.qualification_score})>"