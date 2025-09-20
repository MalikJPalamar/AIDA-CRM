"""
AIDA-CRM Communication API Endpoints
Email and SMS communication management
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
import structlog

from ..core.database import get_db
from ..services.communication_service import CommunicationService

logger = structlog.get_logger()
router = APIRouter(prefix="/communications", tags=["communications"])


class EmailRequest(BaseModel):
    """Request model for sending email"""
    to_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    lead_id: Optional[UUID] = None
    deal_id: Optional[UUID] = None
    template_id: Optional[str] = None
    personalization_data: Optional[Dict[str, Any]] = None
    autonomy_level: int = Field(1, ge=1, le=5)


class SMSRequest(BaseModel):
    """Request model for sending SMS"""
    to_phone: str = Field(..., regex=r'^\+?1?\d{9,15}$')
    message: str = Field(..., min_length=1, max_length=1600)
    lead_id: Optional[UUID] = None
    deal_id: Optional[UUID] = None
    autonomy_level: int = Field(1, ge=1, le=5)


class EmailSequenceRequest(BaseModel):
    """Request model for creating email sequence"""
    lead_id: UUID
    sequence_type: str = Field("welcome", regex=r'^(welcome|nurture|re_engagement)$')
    autonomy_level: int = Field(1, ge=1, le=5)
    delay_hours: List[int] = Field([0, 24, 72, 168])


class EngagementTrackingRequest(BaseModel):
    """Request model for tracking email engagement"""
    event_type: str = Field(..., regex=r'^(opened|clicked|replied)$')
    event_data: Optional[Dict[str, Any]] = None


class CommunicationResponse(BaseModel):
    """Response model for communication"""
    id: str
    type: str
    direction: str
    subject: Optional[str]
    content: str
    status: str
    sent_at: Optional[str]
    opened_at: Optional[str]
    clicked_at: Optional[str]
    replied_at: Optional[str]
    created_at: str


@router.post("/email")
async def send_email(
    request: EmailRequest,
    sender_id: UUID = Query(..., description="ID of the user sending the email"),
    db: AsyncSession = Depends(get_db)
):
    """Send email communication"""
    try:
        comm_service = CommunicationService(db)

        result = await comm_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            content=request.content,
            lead_id=str(request.lead_id) if request.lead_id else None,
            deal_id=str(request.deal_id) if request.deal_id else None,
            sender_id=str(sender_id),
            template_id=request.template_id,
            personalization_data=request.personalization_data,
            autonomy_level=request.autonomy_level
        )

        return {
            "status": "success",
            "message": "Email communication created",
            "data": result
        }

    except Exception as e:
        logger.error("Email send failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )


@router.post("/sms")
async def send_sms(
    request: SMSRequest,
    sender_id: UUID = Query(..., description="ID of the user sending the SMS"),
    db: AsyncSession = Depends(get_db)
):
    """Send SMS communication"""
    try:
        comm_service = CommunicationService(db)

        result = await comm_service.send_sms(
            to_phone=request.to_phone,
            message=request.message,
            lead_id=str(request.lead_id) if request.lead_id else None,
            deal_id=str(request.deal_id) if request.deal_id else None,
            sender_id=str(sender_id),
            autonomy_level=request.autonomy_level
        )

        return {
            "status": "success",
            "message": "SMS communication created",
            "data": result
        }

    except Exception as e:
        logger.error("SMS send failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send SMS"
        )


@router.post("/sequences/email")
async def create_email_sequence(
    request: EmailSequenceRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create automated email sequence for lead nurturing"""
    try:
        comm_service = CommunicationService(db)

        result = await comm_service.create_email_sequence(
            lead_id=str(request.lead_id),
            sequence_type=request.sequence_type,
            autonomy_level=request.autonomy_level,
            delay_hours=request.delay_hours
        )

        return {
            "status": "success",
            "message": "Email sequence created",
            "data": result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Email sequence creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email sequence"
        )


@router.post("/{communication_id}/track")
async def track_engagement(
    communication_id: UUID,
    request: EngagementTrackingRequest,
    db: AsyncSession = Depends(get_db)
):
    """Track email engagement events (opens, clicks, replies)"""
    try:
        comm_service = CommunicationService(db)

        success = await comm_service.track_email_engagement(
            communication_id=str(communication_id),
            event_type=request.event_type,
            event_data=request.event_data
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Communication not found"
            )

        return {
            "status": "success",
            "message": f"Engagement event '{request.event_type}' tracked"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Engagement tracking failed", communication_id=str(communication_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track engagement"
        )


@router.get("/history", response_model=List[CommunicationResponse])
async def get_communication_history(
    lead_id: Optional[UUID] = Query(None, description="Filter by lead ID"),
    deal_id: Optional[UUID] = Query(None, description="Filter by deal ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of communications to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get communication history for a lead or deal"""
    if not lead_id and not deal_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either lead_id or deal_id must be provided"
        )

    try:
        comm_service = CommunicationService(db)

        communications = await comm_service.get_communication_history(
            lead_id=str(lead_id) if lead_id else None,
            deal_id=str(deal_id) if deal_id else None,
            limit=limit
        )

        return [CommunicationResponse(**comm) for comm in communications]

    except Exception as e:
        logger.error("Failed to get communication history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve communication history"
        )


@router.get("/templates")
async def get_email_templates():
    """Get available email templates"""
    # In production, these would be stored in database
    templates = {
        "welcome": {
            "id": "welcome",
            "name": "Welcome Email",
            "description": "Welcome new leads to AIDA-CRM",
            "subject": "Welcome to AIDA-CRM, {{first_name}}!",
            "variables": ["first_name", "company", "source"]
        },
        "follow_up": {
            "id": "follow_up",
            "name": "Follow-up Email",
            "description": "Follow up with qualified leads",
            "subject": "Following up on your interest in AIDA-CRM",
            "variables": ["first_name", "company", "qualification_score"]
        },
        "demo_invite": {
            "id": "demo_invite",
            "name": "Demo Invitation",
            "description": "Invite qualified leads to demo",
            "subject": "Exclusive demo invitation for {{company}}",
            "variables": ["first_name", "last_name", "company"]
        },
        "nurture_content": {
            "id": "nurture_content",
            "name": "Content Nurture",
            "description": "Educational content for lead nurturing",
            "subject": "Industry insights that {{company}} might find valuable",
            "variables": ["first_name", "company", "industry"]
        }
    }

    return {
        "templates": templates,
        "total_count": len(templates)
    }


@router.get("/sequences/types")
async def get_sequence_types():
    """Get available email sequence types"""
    sequence_types = {
        "welcome": {
            "name": "Welcome Sequence",
            "description": "Onboard new leads with welcome series",
            "emails_count": 4,
            "duration_days": 7,
            "recommended_for": ["new_leads", "website_signups"]
        },
        "nurture": {
            "name": "Lead Nurture",
            "description": "Educational content to nurture prospects",
            "emails_count": 4,
            "duration_days": 14,
            "recommended_for": ["qualified_leads", "demo_requests"]
        },
        "re_engagement": {
            "name": "Re-engagement",
            "description": "Re-engage inactive or cold leads",
            "emails_count": 4,
            "duration_days": 10,
            "recommended_for": ["inactive_leads", "cold_prospects"]
        }
    }

    return {
        "sequence_types": sequence_types,
        "total_types": len(sequence_types)
    }


@router.get("/analytics")
async def get_communication_analytics(
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)"),
    communication_type: Optional[str] = Query(None, description="Filter by type (email/sms)"),
    db: AsyncSession = Depends(get_db)
):
    """Get communication analytics and performance metrics"""
    try:
        # In production, implement detailed analytics
        # For now, return mock analytics
        analytics = {
            "summary": {
                "total_sent": 1250,
                "total_delivered": 1198,
                "total_opened": 456,
                "total_clicked": 89,
                "delivery_rate": 0.958,
                "open_rate": 0.381,
                "click_rate": 0.195
            },
            "by_type": {
                "email": {
                    "sent": 1100,
                    "delivered": 1055,
                    "opened": 421,
                    "clicked": 84,
                    "delivery_rate": 0.959,
                    "open_rate": 0.399,
                    "click_rate": 0.199
                },
                "sms": {
                    "sent": 150,
                    "delivered": 143,
                    "opened": 35,
                    "clicked": 5,
                    "delivery_rate": 0.953,
                    "open_rate": 0.245,
                    "click_rate": 0.143
                }
            },
            "top_performing_subjects": [
                {"subject": "Welcome to AIDA-CRM!", "open_rate": 0.65, "click_rate": 0.23},
                {"subject": "Your demo is ready", "open_rate": 0.58, "click_rate": 0.31},
                {"subject": "Industry insights for your business", "open_rate": 0.45, "click_rate": 0.18}
            ]
        }

        return analytics

    except Exception as e:
        logger.error("Failed to get communication analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )