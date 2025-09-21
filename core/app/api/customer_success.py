"""
AIDA-CRM Customer Success API Endpoints
Post-conversion customer lifecycle management
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from ..core.database import get_db
from ..services.customer_success_service import CustomerSuccessService

logger = structlog.get_logger()
router = APIRouter(prefix="/customer-success", tags=["customer_success"])


class OnboardingRequest(BaseModel):
    """Request model for customer onboarding"""
    deal_id: UUID
    onboarding_type: str = Field("standard", regex=r'^(standard|enterprise|self_service)$')
    autonomy_level: int = Field(1, ge=1, le=5)


class HealthScoreResponse(BaseModel):
    """Response model for customer health score"""
    customer_id: str
    health_score: float
    health_category: str
    risk_level: str
    churn_probability: float
    dimensions: Dict[str, float]
    insights: List[Dict[str, str]]
    predictions: Dict[str, Any]
    last_calculated: str
    confidence: float


class ExpansionOpportunityResponse(BaseModel):
    """Response model for expansion opportunities"""
    customer_id: str
    expansion_potential: float
    total_opportunity_value: float
    opportunities: List[Dict[str, Any]]
    expansion_strategy: Dict[str, Any]
    recommended_actions: List[str]
    confidence: float
    autonomy_level: int


class RetentionCampaignRequest(BaseModel):
    """Request model for retention campaign"""
    customer_id: UUID
    campaign_type: str = Field("proactive", regex=r'^(proactive|reactive|win_back)$')
    risk_level: str = Field("medium", regex=r'^(low|medium|high|critical)$')
    autonomy_level: int = Field(1, ge=1, le=5)


class CustomerSuccessAnalyticsResponse(BaseModel):
    """Response model for customer success analytics"""
    period: Dict[str, str]
    customer_metrics: Dict[str, Any]
    health_distribution: Dict[str, int]
    retention_metrics: Dict[str, Any]
    expansion_metrics: Dict[str, Any]
    predictive_insights: List[Dict[str, str]]


@router.post("/onboarding/initiate")
async def initiate_customer_onboarding(
    request: OnboardingRequest,
    db: AsyncSession = Depends(get_db)
):
    """Initiate customer onboarding workflow after deal closure"""
    try:
        cs_service = CustomerSuccessService(db)

        result = await cs_service.initiate_customer_onboarding(
            deal_id=request.deal_id,
            onboarding_type=request.onboarding_type,
            autonomy_level=request.autonomy_level
        )

        return {
            "status": "success",
            "message": "Customer onboarding initiated",
            "data": result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Customer onboarding initiation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate customer onboarding"
        )


@router.get("/health-score/{customer_id}", response_model=HealthScoreResponse)
async def get_customer_health_score(
    customer_id: UUID,
    include_predictions: bool = Query(True, description="Include health predictions"),
    db: AsyncSession = Depends(get_db)
):
    """Calculate comprehensive customer health score"""
    try:
        cs_service = CustomerSuccessService(db)

        health_data = await cs_service.calculate_customer_health_score(
            customer_id=customer_id,
            include_predictions=include_predictions
        )

        return HealthScoreResponse(**health_data)

    except Exception as e:
        logger.error("Health score calculation failed", customer_id=str(customer_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate customer health score"
        )


@router.get("/expansion-opportunities/{customer_id}", response_model=ExpansionOpportunityResponse)
async def get_expansion_opportunities(
    customer_id: UUID,
    autonomy_level: int = Query(1, ge=1, le=5, description="Autonomy level for recommendations"),
    db: AsyncSession = Depends(get_db)
):
    """Identify upsell and expansion opportunities"""
    try:
        cs_service = CustomerSuccessService(db)

        opportunities = await cs_service.identify_expansion_opportunities(
            customer_id=customer_id,
            autonomy_level=autonomy_level
        )

        return ExpansionOpportunityResponse(**opportunities)

    except Exception as e:
        logger.error("Expansion opportunity identification failed", customer_id=str(customer_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to identify expansion opportunities"
        )


@router.post("/retention/campaign")
async def execute_retention_campaign(
    request: RetentionCampaignRequest,
    db: AsyncSession = Depends(get_db)
):
    """Execute targeted retention campaign for at-risk customers"""
    try:
        cs_service = CustomerSuccessService(db)

        result = await cs_service.execute_retention_campaign(
            customer_id=request.customer_id,
            campaign_type=request.campaign_type,
            risk_level=request.risk_level,
            autonomy_level=request.autonomy_level
        )

        return {
            "status": "success",
            "message": "Retention campaign executed",
            "data": result
        }

    except Exception as e:
        logger.error("Retention campaign execution failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute retention campaign"
        )


@router.get("/analytics", response_model=CustomerSuccessAnalyticsResponse)
async def get_customer_success_analytics(
    date_from: Optional[datetime] = Query(None, description="Start date for analytics"),
    date_to: Optional[datetime] = Query(None, description="End date for analytics"),
    segment: Optional[str] = Query(None, description="Customer segment filter"),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive customer success analytics"""
    try:
        cs_service = CustomerSuccessService(db)

        analytics = await cs_service.get_customer_success_analytics(
            date_from=date_from,
            date_to=date_to,
            segment=segment
        )

        return CustomerSuccessAnalyticsResponse(**analytics)

    except Exception as e:
        logger.error("Customer success analytics failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer success analytics"
        )


@router.get("/customers")
async def list_customers(
    health_category: Optional[str] = Query(None, description="Filter by health category"),
    risk_level: Optional[str] = Query(None, description="Filter by retention risk"),
    stage: Optional[str] = Query(None, description="Filter by customer stage"),
    limit: int = Query(50, ge=1, le=100, description="Number of customers to return"),
    offset: int = Query(0, ge=0, description="Number of customers to skip"),
    db: AsyncSession = Depends(get_db)
):
    """List customers with health and risk filtering"""
    try:
        # Mock customer list - in production, implement proper querying
        customers = [
            {
                "customer_id": "cust_001",
                "company": "Acme Corp",
                "health_score": 85,
                "health_category": "good",
                "risk_level": "low",
                "stage": "active",
                "total_value": 45000,
                "last_activity": "2024-01-15T10:30:00Z"
            },
            {
                "customer_id": "cust_002",
                "company": "Beta Industries",
                "health_score": 45,
                "health_category": "poor",
                "risk_level": "high",
                "stage": "at_risk",
                "total_value": 12000,
                "last_activity": "2024-01-02T14:20:00Z"
            }
        ]

        # Apply filters
        if health_category:
            customers = [c for c in customers if c["health_category"] == health_category]
        if risk_level:
            customers = [c for c in customers if c["risk_level"] == risk_level]
        if stage:
            customers = [c for c in customers if c["stage"] == stage]

        # Apply pagination
        total_count = len(customers)
        customers = customers[offset:offset + limit]

        return {
            "customers": customers,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error("Failed to list customers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer list"
        )


@router.get("/customers/{customer_id}/timeline")
async def get_customer_timeline(
    customer_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get customer interaction timeline"""
    try:
        # Mock timeline data
        timeline = [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "event_type": "communication",
                "description": "Outbound email sent - Product update",
                "details": {"type": "email", "subject": "New features available"}
            },
            {
                "timestamp": "2024-01-10T14:20:00Z",
                "event_type": "deal_progression",
                "description": "Deal progressed to Closed Won",
                "details": {"deal_id": "deal_123", "value": 25000}
            },
            {
                "timestamp": "2024-01-05T09:15:00Z",
                "event_type": "health_score_change",
                "description": "Health score increased from 75 to 85",
                "details": {"old_score": 75, "new_score": 85, "reason": "increased_engagement"}
            }
        ]

        return {
            "customer_id": str(customer_id),
            "timeline": timeline[:limit],
            "total_events": len(timeline)
        }

    except Exception as e:
        logger.error("Failed to get customer timeline", customer_id=str(customer_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer timeline"
        )


@router.post("/customers/{customer_id}/health-score/recalculate")
async def recalculate_health_score(
    customer_id: UUID,
    force_update: bool = Query(False, description="Force recalculation even if recent"),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger health score recalculation"""
    try:
        cs_service = CustomerSuccessService(db)

        health_data = await cs_service.calculate_customer_health_score(
            customer_id=customer_id,
            include_predictions=True
        )

        return {
            "status": "success",
            "message": "Health score recalculated",
            "data": {
                "customer_id": str(customer_id),
                "new_health_score": health_data["health_score"],
                "health_category": health_data["health_category"],
                "calculated_at": health_data["last_calculated"]
            }
        }

    except Exception as e:
        logger.error("Health score recalculation failed", customer_id=str(customer_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recalculate health score"
        )


@router.get("/playbooks")
async def get_customer_success_playbooks():
    """Get available customer success playbooks"""
    playbooks = {
        "onboarding": {
            "standard": {
                "name": "Standard Onboarding",
                "duration": "30 days",
                "milestones": ["Account Setup", "Initial Training", "First Success", "Optimization"],
                "success_rate": 0.85
            },
            "enterprise": {
                "name": "Enterprise Onboarding",
                "duration": "60 days",
                "milestones": ["Kickoff Call", "Technical Setup", "Team Training", "Pilot Launch", "Full Rollout"],
                "success_rate": 0.92
            },
            "self_service": {
                "name": "Self-Service Onboarding",
                "duration": "14 days",
                "milestones": ["Account Activation", "First Use", "Feature Adoption"],
                "success_rate": 0.78
            }
        },
        "retention": {
            "proactive": {
                "name": "Proactive Retention",
                "description": "Regular check-ins and value reinforcement",
                "trigger": "Declining health score",
                "success_rate": 0.75
            },
            "reactive": {
                "name": "Reactive Retention",
                "description": "Response to churn signals",
                "trigger": "Support escalation or negative feedback",
                "success_rate": 0.65
            },
            "win_back": {
                "name": "Win-Back Campaign",
                "description": "Re-engage churned customers",
                "trigger": "Post-churn follow-up",
                "success_rate": 0.35
            }
        },
        "expansion": {
            "upsell": {
                "name": "Feature Upsell",
                "description": "Upgrade to premium features",
                "indicators": ["Feature limit reached", "High usage"],
                "average_deal_size": 15000
            },
            "cross_sell": {
                "name": "Product Cross-Sell",
                "description": "Additional product modules",
                "indicators": ["Successful primary product", "Team growth"],
                "average_deal_size": 25000
            },
            "seat_expansion": {
                "name": "Seat Expansion",
                "description": "Additional user licenses",
                "indicators": ["Team growth", "High adoption"],
                "average_deal_size": 8000
            }
        }
    }

    return {
        "playbooks": playbooks,
        "total_categories": len(playbooks),
        "recommendations": {
            "high_value_customers": "Use enterprise onboarding playbook",
            "at_risk_customers": "Deploy proactive retention playbook",
            "engaged_customers": "Evaluate for expansion opportunities"
        }
    }


@router.get("/metrics/benchmarks")
async def get_customer_success_benchmarks():
    """Get industry benchmarks for customer success metrics"""
    benchmarks = {
        "health_scores": {
            "excellent_threshold": 90,
            "good_threshold": 70,
            "fair_threshold": 50,
            "poor_threshold": 30,
            "industry_average": 72
        },
        "retention_rates": {
            "monthly_churn_benchmark": 0.05,
            "annual_churn_benchmark": 0.15,
            "net_retention_benchmark": 1.10,
            "gross_retention_benchmark": 0.90
        },
        "expansion_rates": {
            "upsell_rate_benchmark": 0.25,
            "cross_sell_rate_benchmark": 0.15,
            "expansion_revenue_benchmark": 0.30
        },
        "onboarding_metrics": {
            "time_to_value_benchmark": 30,  # days
            "activation_rate_benchmark": 0.80,
            "first_month_retention_benchmark": 0.95
        },
        "engagement_metrics": {
            "monthly_active_users_benchmark": 0.70,
            "feature_adoption_benchmark": 0.60,
            "support_ticket_rate_benchmark": 0.15
        }
    }

    return {
        "benchmarks": benchmarks,
        "last_updated": "2024-01-01",
        "data_source": "Industry research and internal analysis",
        "note": "Benchmarks vary by industry and customer segment"
    }


@router.post("/customers/{customer_id}/interventions")
async def create_customer_intervention(
    customer_id: UUID,
    intervention_type: str = Field(..., description="Type of intervention"),
    priority: str = Field("medium", regex=r'^(low|medium|high|critical)$'),
    assigned_to: Optional[UUID] = Field(None, description="User to assign intervention to"),
    notes: Optional[str] = Field(None, max_length=1000),
    db: AsyncSession = Depends(get_db)
):
    """Create a customer intervention record"""
    try:
        intervention_id = f"int_{customer_id}_{int(datetime.utcnow().timestamp())}"

        intervention = {
            "intervention_id": intervention_id,
            "customer_id": str(customer_id),
            "type": intervention_type,
            "priority": priority,
            "assigned_to": str(assigned_to) if assigned_to else None,
            "notes": notes,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }

        # In production, save to database
        logger.info(
            "Customer intervention created",
            customer_id=str(customer_id),
            intervention_id=intervention_id,
            type=intervention_type
        )

        return {
            "status": "success",
            "message": "Customer intervention created",
            "data": intervention
        }

    except Exception as e:
        logger.error("Failed to create customer intervention", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer intervention"
        )