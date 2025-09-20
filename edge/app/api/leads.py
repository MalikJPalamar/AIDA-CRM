"""
AIDA-CRM Edge API Lead Management Endpoints
"""

import httpx
from fastapi import APIRouter, HTTPException, status, Depends, Request
import structlog

from ..core.config import settings
from ..core.security import get_current_user
from ..models.requests import LeadCaptureRequest
from ..models.responses import LeadCaptureResponse, ResponseStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/capture", response_model=LeadCaptureResponse)
async def capture_lead(
    lead_request: LeadCaptureRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Capture a new lead"""
    try:
        # Enrich lead data with request metadata
        enriched_data = lead_request.model_dump()
        enriched_data.update({
            "user_id": current_user.get("sub"),
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "referer": request.headers.get("referer"),
        })

        # Forward to core API for processing
        async with httpx.AsyncClient(timeout=settings.core_api_timeout) as client:
            response = await client.post(
                f"{settings.core_api_url}/api/v1/leads/capture",
                json=enriched_data,
                headers={"Authorization": f"Bearer {request.headers.get('authorization', '').replace('Bearer ', '')}"}
            )

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Lead capture failed")
                logger.warning(
                    "Lead capture failed at core API",
                    email=lead_request.email,
                    status_code=response.status_code,
                    error=error_detail
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )

            result = response.json()

        logger.info(
            "Lead captured successfully",
            lead_id=result.get("lead_id"),
            email=lead_request.email,
            source=lead_request.source
        )

        return LeadCaptureResponse(
            status=ResponseStatus.SUCCESS,
            message="Lead captured successfully",
            lead_id=result.get("lead_id"),
            qualification_score=result.get("qualification_score"),
            next_actions=result.get("next_actions", [])
        )

    except httpx.RequestError as e:
        logger.error("Core API connection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lead capture service temporarily unavailable"
        )
    except Exception as e:
        logger.error("Lead capture error", error=str(e), email=lead_request.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal lead capture error"
        )


@router.get("/")
async def list_leads(
    limit: int = 50,
    offset: int = 0,
    source: str = None,
    current_user: dict = Depends(get_current_user)
):
    """List leads with pagination and filtering"""
    try:
        params = {
            "limit": limit,
            "offset": offset,
            "user_id": current_user.get("sub")
        }
        if source:
            params["source"] = source

        async with httpx.AsyncClient(timeout=settings.core_api_timeout) as client:
            response = await client.get(
                f"{settings.core_api_url}/api/v1/leads/",
                params=params
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to retrieve leads"
                )

            return response.json()

    except httpx.RequestError as e:
        logger.error("Core API connection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lead service temporarily unavailable"
        )


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific lead by ID"""
    try:
        async with httpx.AsyncClient(timeout=settings.core_api_timeout) as client:
            response = await client.get(
                f"{settings.core_api_url}/api/v1/leads/{lead_id}",
                params={"user_id": current_user.get("sub")}
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lead not found"
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to retrieve lead"
                )

            return response.json()

    except httpx.RequestError as e:
        logger.error("Core API connection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lead service temporarily unavailable"
        )