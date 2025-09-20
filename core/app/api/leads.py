"""
AIDA-CRM Core API Lead Endpoints
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
import structlog

from ..core.database import get_db
from ..services.lead_service import LeadService

logger = structlog.get_logger()
router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCaptureRequest(BaseModel):
    """Request model for lead capture"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    source: str = "web"
    campaign: Optional[str] = None
    utm_params: Optional[dict] = None
    custom_fields: Optional[dict] = None
    user_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None


class LeadResponse(BaseModel):
    """Response model for lead data"""
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    company: Optional[str]
    phone: Optional[str]
    source: str
    campaign: Optional[str]
    qualification_score: Optional[float]
    status: str
    is_qualified: bool
    created_at: Optional[str]


class LeadCaptureResponse(BaseModel):
    """Response model for lead capture"""
    lead_id: str
    qualification_score: Optional[float]
    status: str
    next_actions: List[str]
    duplicate: bool = False


@router.post("/capture", response_model=LeadCaptureResponse)
async def capture_lead(
    request: LeadCaptureRequest,
    db: AsyncSession = Depends(get_db)
):
    """Capture a new lead"""
    try:
        lead_service = LeadService(db)

        result = await lead_service.capture_lead(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            company=request.company,
            phone=request.phone,
            source=request.source,
            campaign=request.campaign,
            utm_params=request.utm_params,
            custom_fields=request.custom_fields,
            user_id=request.user_id,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            referer=request.referer
        )

        return LeadCaptureResponse(**result)

    except Exception as e:
        logger.error("Lead capture failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture lead"
        )


@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    user_id: Optional[UUID] = Query(None, description="Filter by assigned user"),
    status: Optional[str] = Query(None, description="Filter by lead status"),
    source: Optional[str] = Query(None, description="Filter by lead source"),
    limit: int = Query(50, ge=1, le=100, description="Number of leads to return"),
    offset: int = Query(0, ge=0, description="Number of leads to skip"),
    db: AsyncSession = Depends(get_db)
):
    """List leads with filtering and pagination"""
    try:
        lead_service = LeadService(db)

        leads = await lead_service.get_leads(
            user_id=user_id,
            status=status,
            source=source,
            limit=limit,
            offset=offset
        )

        return [LeadResponse(**lead) for lead in leads]

    except Exception as e:
        logger.error("Failed to list leads", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leads"
        )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific lead by ID"""
    try:
        lead_service = LeadService(db)
        lead = await lead_service.get_lead_by_id(lead_id)

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )

        return LeadResponse(**lead)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get lead", lead_id=str(lead_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lead"
        )


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: UUID,
    status: str = Field(..., description="New lead status"),
    user_id: Optional[UUID] = Field(None, description="Assign to user"),
    db: AsyncSession = Depends(get_db)
):
    """Update lead status"""
    try:
        lead_service = LeadService(db)

        success = await lead_service.update_lead_status(
            lead_id=lead_id,
            status=status,
            user_id=user_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found"
            )

        return {"message": "Lead status updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update lead status", lead_id=str(lead_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update lead status"
        )