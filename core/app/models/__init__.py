"""
AIDA-CRM Core Models
"""

from .users import User
from .leads import Lead, LeadStatus
from .deals import Deal, DealStage
from .communications import Communication, CommunicationType, CommunicationDirection, CommunicationStatus
from .events import Event, EventStatus

__all__ = [
    "User",
    "Lead",
    "LeadStatus",
    "Deal",
    "DealStage",
    "Communication",
    "CommunicationType",
    "CommunicationDirection",
    "CommunicationStatus",
    "Event",
    "EventStatus",
]