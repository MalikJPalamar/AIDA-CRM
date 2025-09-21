"""
AIDA-CRM Deal API Endpoints
Complete deal pipeline management
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from ..core.database import get_db
from ..services.deal_service import DealService

logger = structlog.get_logger()
router = APIRouter(prefix="/deals", tags=["deals"])


class CreateDealRequest(BaseModel):
    """Request model for creating deal from lead"""
    lead_id: UUID
    title: Optional[str] = None
    value: Optional[Decimal] = Field(None, gt=0)
    expected_close_date: Optional[datetime] = None
    assigned_to: Optional[UUID] = None
    autonomy_level: int = Field(1, ge=1, le=5)


class ProgressDealRequest(BaseModel):
    """Request model for progressing deal stage"""
    new_stage: str = Field(..., regex=r'^(prospect|qualified|proposal|negotiation|closed_won|closed_lost)$')
    reason: Optional[str] = Field(None, max_length=500)
    autonomy_level: int = Field(1, ge=1, le=5)


class UpdateValueRequest(BaseModel):
    """Request model for updating deal value"""
    new_value: Decimal = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)
    autonomy_level: int = Field(1, ge=1, le=5)


class DealResponse(BaseModel):
    """Response model for deal data"""
    id: str
    lead_id: Optional[str]
    title: str
    description: Optional[str]
    value: Optional[float]
    currency: str
    stage: str
    probability: int
    expected_close_date: Optional[str]
    assigned_to: Optional[str]
    is_won: bool
    is_lost: bool
    is_closed: bool
    weighted_value: float
    created_at: str
    updated_at: str


class PipelineAnalyticsResponse(BaseModel):
    """Response model for pipeline analytics"""
    period: Dict[str, str]
    summary: Dict[str, Any]
    forecast: Dict[str, Any]
    stage_analysis: Dict[str, Any]
    performance: Dict[str, Any]
    total_deals: int


@router.post("/create-from-lead")
async def create_deal_from_lead(
    request: CreateDealRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new deal from a qualified lead"""
    try:
        deal_service = DealService(db)

        result = await deal_service.create_deal_from_lead(
            lead_id=request.lead_id,
            title=request.title,
            value=request.value,
            expected_close_date=request.expected_close_date,
            assigned_to=request.assigned_to,
            autonomy_level=request.autonomy_level
        )

        return {
            "status": "success",
            "message": "Deal created from qualified lead",
            "data": result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Deal creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create deal"
        )


@router.post("/{deal_id}/progress")
async def progress_deal(
    deal_id: UUID,
    request: ProgressDealRequest,
    user_id: UUID = Query(..., description="ID of user making the change"),
    db: AsyncSession = Depends(get_db)
):
    """Progress deal to new stage"""
    try:
        deal_service = DealService(db)

        result = await deal_service.progress_deal(
            deal_id=deal_id,
            new_stage=request.new_stage,
            reason=request.reason,
            autonomy_level=request.autonomy_level,
            user_id=user_id
        )

        return {
            "status": "success",
            "message": "Deal progression processed",
            "data": result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Deal progression failed", deal_id=str(deal_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to progress deal"
        )


@router.patch("/{deal_id}/value")
async def update_deal_value(
    deal_id: UUID,
    request: UpdateValueRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update deal value"""
    try:
        deal_service = DealService(db)

        result = await deal_service.update_deal_value(
            deal_id=deal_id,
            new_value=request.new_value,
            reason=request.reason,
            autonomy_level=request.autonomy_level
        )

        return {
            "status": "success",
            "message": "Deal value update processed",
            "data": result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Deal value update failed", deal_id=str(deal_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update deal value"
        )


@router.get("/", response_model=List[DealResponse])
async def list_deals(
    stage: Optional[str] = Query(None, description="Filter by deal stage"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned user"),
    limit: int = Query(50, ge=1, le=100, description="Number of deals to return"),
    offset: int = Query(0, ge=0, description="Number of deals to skip"),
    db: AsyncSession = Depends(get_db)
):
    """List deals with filtering and pagination"""
    try:
        # This would be implemented in the deal service
        # For now, return mock data structure
        return []

    except Exception as e:
        logger.error("Failed to list deals", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deals"
        )


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific deal by ID"""
    try:
        # This would be implemented in the deal service
        # For now, return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get deal", deal_id=str(deal_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deal"
        )


@router.get("/pipeline/analytics", response_model=PipelineAnalyticsResponse)
async def get_pipeline_analytics(
    date_from: Optional[datetime] = Query(None, description="Start date for analytics"),
    date_to: Optional[datetime] = Query(None, description="End date for analytics"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned user"),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive pipeline analytics"""
    try:
        deal_service = DealService(db)

        analytics = await deal_service.get_pipeline_analytics(
            date_from=date_from,
            date_to=date_to,
            assigned_to=assigned_to
        )

        return PipelineAnalyticsResponse(**analytics)

    except Exception as e:
        logger.error("Pipeline analytics failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pipeline analytics"
        )


@router.get("/stages/definitions")
async def get_stage_definitions():
    """Get deal stage definitions and transitions"""
    return {
        "stages": {
            "prospect": {
                "name": "Prospect",
                "description": "Initial contact established",
                "typical_probability": 10,
                "next_stages": ["qualified", "closed_lost"]
            },
            "qualified": {
                "name": "Qualified",
                "description": "Lead meets qualification criteria",
                "typical_probability": 25,
                "next_stages": ["proposal", "closed_lost"]
            },
            "proposal": {
                "name": "Proposal",
                "description": "Proposal presented to prospect",
                "typical_probability": 50,
                "next_stages": ["negotiation", "qualified", "closed_lost"]
            },
            "negotiation": {
                "name": "Negotiation",
                "description": "Contract terms being negotiated",
                "typical_probability": 75,
                "next_stages": ["closed_won", "proposal", "closed_lost"]
            },
            "closed_won": {
                "name": "Closed Won",
                "description": "Deal successfully closed",
                "typical_probability": 100,
                "next_stages": []
            },
            "closed_lost": {
                "name": "Closed Lost",
                "description": "Deal was not successful",
                "typical_probability": 0,
                "next_stages": ["qualified"]
            }
        },
        "autonomy_guidelines": {
            "L1": "All progressions require manual approval",
            "L2": "High-confidence progressions allowed with review",
            "L3": "Standard progressions automated, exceptions escalated",
            "L4": "Aggressive automation with minimal oversight",
            "L5": "Full automation with human-on-the-loop monitoring"
        }
    }


@router.get("/forecasting/methods")
async def get_forecasting_methods():
    """Get available forecasting methods and parameters"""
    return {
        "methods": {
            "probability_weighted": {
                "name": "Probability Weighted",
                "description": "Forecast based on deal value × probability",
                "accuracy": "Medium",
                "confidence": 0.7
            },
            "historical_trend": {
                "name": "Historical Trend",
                "description": "Forecast based on historical close patterns",
                "accuracy": "High",
                "confidence": 0.8
            },
            "ai_predictive": {
                "name": "AI Predictive",
                "description": "Machine learning-based forecasting",
                "accuracy": "Very High",
                "confidence": 0.9
            }
        },
        "current_method": "probability_weighted",
        "forecast_horizons": [30, 60, 90, 180],
        "confidence_factors": [
            "Deal age",
            "Communication frequency",
            "Stage progression history",
            "Customer profile match"
        ]
    }


@router.post("/{deal_id}/notes")
async def add_deal_note(
    deal_id: UUID,
    note: str = Field(..., min_length=1, max_length=2000),
    note_type: str = Field("general", regex=r'^(general|meeting|call|email|internal)$'),
    user_id: UUID = Query(..., description="ID of user adding the note"),
    db: AsyncSession = Depends(get_db)
):
    """Add a note to a deal"""
    try:
        # In a full implementation, this would:
        # 1. Validate deal exists
        # 2. Create note record
        # 3. Publish event
        # 4. Return confirmation

        return {
            "status": "success",
            "message": "Note added to deal",
            "note_id": "note_123",
            "deal_id": str(deal_id)
        }

    except Exception as e:
        logger.error("Failed to add deal note", deal_id=str(deal_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add note"
        )


@router.get("/reports/conversion")
async def get_conversion_report(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    source: Optional[str] = Query(None, description="Filter by lead source"),
    db: AsyncSession = Depends(get_db)
):
    """Get lead-to-deal conversion report"""
    try:
        # Mock conversion analytics
        conversion_data = {
            "period": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            },
            "summary": {
                "total_leads": 1250,
                "converted_deals": 156,
                "conversion_rate": 0.125,
                "average_time_to_convert_days": 12,
                "total_converted_value": 1875000
            },
            "by_source": {
                "demo_request": {"leads": 45, "deals": 12, "rate": 0.267, "avg_value": 25000},
                "pricing_page": {"leads": 78, "deals": 15, "rate": 0.192, "avg_value": 18000},
                "webinar": {"leads": 156, "deals": 18, "rate": 0.115, "avg_value": 12000},
                "content_download": {"leads": 234, "deals": 21, "rate": 0.090, "avg_value": 8000}
            },
            "trends": {
                "conversion_rate_trend": "increasing",
                "average_deal_value_trend": "stable",
                "time_to_convert_trend": "decreasing"
            }
        }

        return conversion_data

    except Exception as e:
        logger.error("Conversion report failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate conversion report"
        )