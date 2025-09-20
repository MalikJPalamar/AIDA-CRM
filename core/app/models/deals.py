"""
AIDA-CRM Deal Models
"""

from sqlalchemy import Column, String, Numeric, DateTime, Text, ForeignKey, Integer, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from ..core.database import Base


class DealStage(str, Enum):
    """Deal stage enumeration"""
    PROSPECT = "prospect"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class Deal(Base):
    """Deal model for tracking sales opportunities"""
    __tablename__ = "deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    value = Column(Numeric(12, 2))
    currency = Column(String(3), default="USD")
    stage = Column(String(50), default=DealStage.PROSPECT.value)
    probability = Column(
        Integer,
        default=10,
        CheckConstraint('probability >= 0 AND probability <= 100')
    )
    expected_close_date = Column(Date)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="deals")
    assigned_user = relationship("User", backref="assigned_deals")
    communications = relationship("Communication", back_populates="deal")

    @property
    def is_won(self) -> bool:
        """Check if deal is won"""
        return self.stage == DealStage.CLOSED_WON.value

    @property
    def is_lost(self) -> bool:
        """Check if deal is lost"""
        return self.stage == DealStage.CLOSED_LOST.value

    @property
    def is_closed(self) -> bool:
        """Check if deal is closed (won or lost)"""
        return self.is_won or self.is_lost

    @property
    def weighted_value(self) -> float:
        """Calculate weighted value based on probability"""
        if self.value and self.probability:
            return float(self.value) * (self.probability / 100)
        return 0.0

    def __repr__(self):
        return f"<Deal(title='{self.title}', stage='{self.stage}', value={self.value})>"