"""
AIDA-CRM Customer Success Service
Post-conversion customer lifecycle management and retention workflows
"""

from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
import structlog

from ..models.deals import Deal, DealStage
from ..models.leads import Lead
from ..models.communications import Communication
from ..services.ai_service import AIService
from ..services.communication_service import CommunicationService
from ..services.nats_client import get_nats_client
from ..core.config import settings

logger = structlog.get_logger()


class CustomerStage(str, Enum):
    """Customer lifecycle stages"""
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    ENGAGED = "engaged"
    AT_RISK = "at_risk"
    CHURNED = "churned"
    EXPANSION_READY = "expansion_ready"


class HealthScore(str, Enum):
    """Customer health score categories"""
    EXCELLENT = "excellent"    # 90-100
    GOOD = "good"             # 70-89
    FAIR = "fair"             # 50-69
    POOR = "poor"             # 30-49
    CRITICAL = "critical"     # 0-29


class RetentionRisk(str, Enum):
    """Customer retention risk levels"""
    LOW = "low"               # < 20% churn probability
    MEDIUM = "medium"         # 20-50% churn probability
    HIGH = "high"             # 50-80% churn probability
    CRITICAL = "critical"     # > 80% churn probability


class CustomerSuccessService:
    """Service for customer success and retention management"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.communication_service = CommunicationService(db)

    async def initiate_customer_onboarding(
        self,
        deal_id: UUID,
        onboarding_type: str = "standard",
        autonomy_level: int = 1
    ) -> Dict[str, Any]:
        """Initiate customer onboarding workflow after deal closure"""

        try:
            # Get deal information
            deal_query = select(Deal).where(Deal.id == deal_id)
            deal_result = await self.db.execute(deal_query)
            deal = deal_result.scalar_one_or_none()

            if not deal:
                raise ValueError(f"Deal {deal_id} not found")

            if not deal.is_won:
                raise ValueError(f"Deal must be won to initiate onboarding. Current stage: {deal.stage}")

            # Get lead information
            lead_query = select(Lead).where(Lead.id == deal.lead_id)
            lead_result = await self.db.execute(lead_query)
            lead = lead_result.scalar_one_or_none()

            # Analyze customer profile for onboarding customization
            customer_profile = await self._analyze_customer_profile(deal, lead)

            # Create onboarding plan
            onboarding_plan = await self._create_onboarding_plan(
                deal, customer_profile, onboarding_type, autonomy_level
            )

            # Initialize customer health tracking
            initial_health = await self._initialize_health_tracking(deal, customer_profile)

            # Schedule onboarding activities
            scheduled_activities = await self._schedule_onboarding_activities(
                deal, onboarding_plan, autonomy_level
            )

            # Publish onboarding event
            await self._publish_customer_event("customer.onboarding_started", deal, {
                "onboarding_type": onboarding_type,
                "plan": onboarding_plan,
                "initial_health": initial_health
            })

            result = {
                "deal_id": str(deal_id),
                "customer_id": str(deal.lead_id) if deal.lead_id else None,
                "onboarding_type": onboarding_type,
                "customer_profile": customer_profile,
                "onboarding_plan": onboarding_plan,
                "initial_health_score": initial_health["score"],
                "scheduled_activities": len(scheduled_activities),
                "estimated_completion_days": onboarding_plan.get("duration_days", 30),
                "autonomy_level": autonomy_level
            }

            logger.info(
                "Customer onboarding initiated",
                deal_id=str(deal_id),
                onboarding_type=onboarding_type,
                health_score=initial_health["score"]
            )

            return result

        except Exception as e:
            logger.error("Customer onboarding initiation failed", deal_id=str(deal_id), error=str(e))
            raise

    async def calculate_customer_health_score(
        self,
        customer_id: UUID,
        include_predictions: bool = True
    ) -> Dict[str, Any]:
        """Calculate comprehensive customer health score"""

        try:
            # Get customer deals and communications
            customer_data = await self._get_customer_data(customer_id)

            # Calculate health dimensions
            health_dimensions = await self._calculate_health_dimensions(customer_data)

            # Compute composite health score
            composite_score = self._compute_composite_health_score(health_dimensions)

            # Categorize health
            health_category = self._categorize_health_score(composite_score)

            # Generate insights
            insights = await self._generate_health_insights(health_dimensions, composite_score)

            # Predict future health if requested
            predictions = {}
            if include_predictions:
                predictions = await self._predict_health_trajectory(customer_data, health_dimensions)

            # Determine risk level
            risk_assessment = self._assess_retention_risk(health_dimensions, composite_score)

            result = {
                "customer_id": str(customer_id),
                "health_score": composite_score,
                "health_category": health_category.value,
                "risk_level": risk_assessment["risk_level"].value,
                "churn_probability": risk_assessment["churn_probability"],
                "dimensions": health_dimensions,
                "insights": insights,
                "predictions": predictions,
                "last_calculated": datetime.utcnow().isoformat(),
                "confidence": 0.85
            }

            logger.info(
                "Customer health score calculated",
                customer_id=str(customer_id),
                score=composite_score,
                category=health_category.value,
                risk=risk_assessment["risk_level"].value
            )

            return result

        except Exception as e:
            logger.error("Health score calculation failed", customer_id=str(customer_id), error=str(e))
            raise

    async def identify_expansion_opportunities(
        self,
        customer_id: UUID,
        autonomy_level: int = 1
    ) -> Dict[str, Any]:
        """Identify upsell and expansion opportunities"""

        try:
            # Get customer data and usage patterns
            customer_data = await self._get_customer_data(customer_id)
            usage_patterns = await self._analyze_usage_patterns(customer_data)

            # AI-powered expansion analysis
            expansion_analysis = await self._analyze_expansion_potential(customer_data, usage_patterns)

            # Identify specific opportunities
            opportunities = await self._identify_specific_opportunities(
                customer_data, expansion_analysis, autonomy_level
            )

            # Calculate opportunity value and prioritize
            prioritized_opportunities = self._prioritize_opportunities(opportunities)

            # Generate expansion strategy
            expansion_strategy = await self._create_expansion_strategy(
                prioritized_opportunities, autonomy_level
            )

            result = {
                "customer_id": str(customer_id),
                "expansion_potential": expansion_analysis.get("potential_score", 0.5),
                "total_opportunity_value": sum(
                    opp.get("estimated_value", 0) for opp in prioritized_opportunities
                ),
                "opportunities": prioritized_opportunities,
                "expansion_strategy": expansion_strategy,
                "recommended_actions": expansion_strategy.get("immediate_actions", []),
                "confidence": expansion_analysis.get("confidence", 0.7),
                "autonomy_level": autonomy_level
            }

            logger.info(
                "Expansion opportunities identified",
                customer_id=str(customer_id),
                opportunity_count=len(prioritized_opportunities),
                total_value=result["total_opportunity_value"]
            )

            return result

        except Exception as e:
            logger.error("Expansion opportunity identification failed", customer_id=str(customer_id), error=str(e))
            raise

    async def execute_retention_campaign(
        self,
        customer_id: UUID,
        campaign_type: str = "proactive",
        risk_level: str = "medium",
        autonomy_level: int = 1
    ) -> Dict[str, Any]:
        """Execute targeted retention campaign for at-risk customers"""

        try:
            # Get customer data
            customer_data = await self._get_customer_data(customer_id)

            # Analyze retention factors
            retention_analysis = await self._analyze_retention_factors(customer_data, risk_level)

            # Design retention campaign
            campaign_design = await self._design_retention_campaign(
                customer_data, retention_analysis, campaign_type, autonomy_level
            )

            # Execute campaign activities
            campaign_execution = await self._execute_campaign_activities(
                customer_id, campaign_design, autonomy_level
            )

            # Set up monitoring and tracking
            monitoring_setup = await self._setup_campaign_monitoring(
                customer_id, campaign_design, campaign_execution
            )

            # Publish retention event
            await self._publish_customer_event("customer.retention_campaign_started", None, {
                "customer_id": str(customer_id),
                "campaign_type": campaign_type,
                "risk_level": risk_level,
                "campaign_design": campaign_design
            })

            result = {
                "customer_id": str(customer_id),
                "campaign_id": campaign_execution.get("campaign_id"),
                "campaign_type": campaign_type,
                "risk_level": risk_level,
                "retention_analysis": retention_analysis,
                "campaign_activities": len(campaign_design.get("activities", [])),
                "executed_activities": len(campaign_execution.get("executed_activities", [])),
                "monitoring_metrics": monitoring_setup.get("tracked_metrics", []),
                "expected_duration_days": campaign_design.get("duration_days", 14),
                "autonomy_level": autonomy_level
            }

            logger.info(
                "Retention campaign executed",
                customer_id=str(customer_id),
                campaign_id=result["campaign_id"],
                campaign_type=campaign_type,
                activities=result["campaign_activities"]
            )

            return result

        except Exception as e:
            logger.error("Retention campaign execution failed", customer_id=str(customer_id), error=str(e))
            raise

    async def get_customer_success_analytics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive customer success analytics"""

        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=90)
            if not date_to:
                date_to = datetime.utcnow()

            # Get customer metrics
            customer_metrics = await self._calculate_customer_metrics(date_from, date_to, segment)

            # Health distribution
            health_distribution = await self._calculate_health_distribution()

            # Retention metrics
            retention_metrics = await self._calculate_retention_metrics(date_from, date_to)

            # Expansion metrics
            expansion_metrics = await self._calculate_expansion_metrics(date_from, date_to)

            # Predictive insights
            predictive_insights = await self._generate_predictive_insights(customer_metrics)

            result = {
                "period": {
                    "from": date_from.isoformat(),
                    "to": date_to.isoformat()
                },
                "customer_metrics": customer_metrics,
                "health_distribution": health_distribution,
                "retention_metrics": retention_metrics,
                "expansion_metrics": expansion_metrics,
                "predictive_insights": predictive_insights,
                "segment": segment
            }

            return result

        except Exception as e:
            logger.error("Customer success analytics failed", error=str(e))
            raise

    async def _analyze_customer_profile(self, deal: Deal, lead: Optional[Lead]) -> Dict[str, Any]:
        """Analyze customer profile for onboarding customization"""

        profile = {
            "deal_value": float(deal.value) if deal.value else 0,
            "company_size": "unknown",
            "industry": "unknown",
            "technical_sophistication": "medium",
            "urgency_level": "medium"
        }

        if lead:
            # Analyze company indicators
            company = lead.company or ""
            if any(indicator in company.lower() for indicator in ["enterprise", "corp", "international"]):
                profile["company_size"] = "enterprise"
            elif any(indicator in company.lower() for indicator in ["inc", "llc", "ltd"]):
                profile["company_size"] = "medium"
            else:
                profile["company_size"] = "small"

            # Analyze source for technical sophistication
            if lead.source in ["api", "developer_portal", "github"]:
                profile["technical_sophistication"] = "high"
            elif lead.source in ["demo_request", "pricing_page"]:
                profile["technical_sophistication"] = "medium"
            else:
                profile["technical_sophistication"] = "low"

        # Categorize based on deal value
        if profile["deal_value"] > 50000:
            profile["priority_tier"] = "high"
        elif profile["deal_value"] > 15000:
            profile["priority_tier"] = "medium"
        else:
            profile["priority_tier"] = "standard"

        return profile

    async def _create_onboarding_plan(
        self,
        deal: Deal,
        customer_profile: Dict[str, Any],
        onboarding_type: str,
        autonomy_level: int
    ) -> Dict[str, Any]:
        """Create customized onboarding plan"""

        # Base onboarding templates
        templates = {
            "standard": {
                "duration_days": 30,
                "milestones": ["account_setup", "initial_training", "first_success", "optimization"],
                "touchpoints": 5
            },
            "enterprise": {
                "duration_days": 60,
                "milestones": ["kickoff_call", "technical_setup", "team_training", "pilot_launch", "full_rollout"],
                "touchpoints": 8
            },
            "self_service": {
                "duration_days": 14,
                "milestones": ["account_activation", "first_use", "feature_adoption"],
                "touchpoints": 3
            }
        }

        # Select template based on profile
        priority_tier = customer_profile.get("priority_tier", "standard")
        if priority_tier == "high":
            base_template = templates["enterprise"]
        elif customer_profile.get("technical_sophistication") == "high":
            base_template = templates["self_service"]
        else:
            base_template = templates[onboarding_type]

        # Customize based on customer profile
        plan = base_template.copy()
        plan["customer_profile"] = customer_profile
        plan["customizations"] = self._get_onboarding_customizations(customer_profile)
        plan["success_criteria"] = self._define_success_criteria(customer_profile)

        return plan

    async def _initialize_health_tracking(self, deal: Deal, customer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize customer health tracking"""

        # Initial health score based on deal characteristics
        initial_score = 70  # Base score for new customers

        # Adjust based on profile
        if customer_profile.get("priority_tier") == "high":
            initial_score += 10
        if customer_profile.get("deal_value", 0) > 25000:
            initial_score += 5

        # Ensure score is within bounds
        initial_score = max(0, min(100, initial_score))

        health_data = {
            "score": initial_score,
            "category": self._categorize_health_score(initial_score).value,
            "last_updated": datetime.utcnow().isoformat(),
            "tracking_enabled": True,
            "baseline_metrics": {
                "onboarding_progress": 0,
                "feature_adoption": 0,
                "engagement_level": 0.5,
                "support_interactions": 0
            }
        }

        return health_data

    async def _schedule_onboarding_activities(
        self,
        deal: Deal,
        onboarding_plan: Dict[str, Any],
        autonomy_level: int
    ) -> List[Dict[str, Any]]:
        """Schedule onboarding activities"""

        activities = []
        milestones = onboarding_plan.get("milestones", [])
        duration_days = onboarding_plan.get("duration_days", 30)

        # Calculate activity timing
        days_per_milestone = duration_days / len(milestones) if milestones else 7

        for i, milestone in enumerate(milestones):
            scheduled_date = datetime.utcnow() + timedelta(days=int(i * days_per_milestone))

            activity = {
                "milestone": milestone,
                "scheduled_date": scheduled_date.isoformat(),
                "type": "onboarding",
                "priority": "high" if i < 2 else "medium",
                "automated": autonomy_level >= 3
            }

            activities.append(activity)

        return activities

    async def _get_customer_data(self, customer_id: UUID) -> Dict[str, Any]:
        """Get comprehensive customer data"""

        try:
            # Get deals for this customer (using lead_id as customer_id)
            deals_query = select(Deal).where(Deal.lead_id == customer_id)
            deals_result = await self.db.execute(deals_query)
            deals = deals_result.scalars().all()

            # Get communications
            comms_query = select(Communication).where(Communication.lead_id == customer_id)
            comms_result = await self.db.execute(comms_query)
            communications = comms_result.scalars().all()

            # Get lead data
            lead_query = select(Lead).where(Lead.id == customer_id)
            lead_result = await self.db.execute(lead_query)
            lead = lead_result.scalar_one_or_none()

            return {
                "customer_id": str(customer_id),
                "deals": deals,
                "communications": communications,
                "lead": lead,
                "total_value": sum(float(deal.value) for deal in deals if deal.value),
                "deal_count": len(deals),
                "communication_count": len(communications)
            }

        except Exception as e:
            logger.error("Failed to get customer data", customer_id=str(customer_id), error=str(e))
            return {"customer_id": str(customer_id), "deals": [], "communications": [], "lead": None}

    async def _calculate_health_dimensions(self, customer_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate health score dimensions"""

        dimensions = {}

        # Engagement dimension (0-1)
        communications = customer_data.get("communications", [])
        recent_comms = [c for c in communications if c.created_at > datetime.utcnow() - timedelta(days=30)]
        dimensions["engagement"] = min(1.0, len(recent_comms) / 5)  # Normalize to 5 comms/month

        # Deal performance dimension
        deals = customer_data.get("deals", [])
        won_deals = [d for d in deals if d.is_won]
        dimensions["deal_performance"] = len(won_deals) / max(len(deals), 1) if deals else 0.5

        # Recency dimension
        if communications:
            last_comm = max(communications, key=lambda c: c.created_at)
            days_since_last = (datetime.utcnow() - last_comm.created_at).days
            dimensions["recency"] = max(0, 1 - (days_since_last / 90))  # Decay over 90 days
        else:
            dimensions["recency"] = 0.3

        # Value dimension
        total_value = customer_data.get("total_value", 0)
        if total_value > 100000:
            dimensions["value"] = 1.0
        elif total_value > 25000:
            dimensions["value"] = 0.8
        elif total_value > 5000:
            dimensions["value"] = 0.6
        else:
            dimensions["value"] = 0.4

        # Growth dimension (based on deal progression)
        if len(deals) > 1:
            dimensions["growth"] = 0.8  # Multiple deals indicate growth
        else:
            dimensions["growth"] = 0.5

        return dimensions

    def _compute_composite_health_score(self, dimensions: Dict[str, float]) -> float:
        """Compute composite health score from dimensions"""

        # Weighted combination of dimensions
        weights = {
            "engagement": 0.25,
            "deal_performance": 0.20,
            "recency": 0.20,
            "value": 0.20,
            "growth": 0.15
        }

        composite = 0.0
        total_weight = 0.0

        for dimension, score in dimensions.items():
            weight = weights.get(dimension, 0.1)
            composite += score * weight
            total_weight += weight

        # Normalize and convert to 0-100 scale
        if total_weight > 0:
            composite = (composite / total_weight) * 100

        return max(0, min(100, composite))

    def _categorize_health_score(self, score: float) -> HealthScore:
        """Categorize health score"""

        if score >= 90:
            return HealthScore.EXCELLENT
        elif score >= 70:
            return HealthScore.GOOD
        elif score >= 50:
            return HealthScore.FAIR
        elif score >= 30:
            return HealthScore.POOR
        else:
            return HealthScore.CRITICAL

    async def _generate_health_insights(
        self,
        dimensions: Dict[str, float],
        composite_score: float
    ) -> List[Dict[str, str]]:
        """Generate actionable insights from health analysis"""

        insights = []

        # Dimension-specific insights
        if dimensions.get("engagement", 0) < 0.3:
            insights.append({
                "type": "warning",
                "dimension": "engagement",
                "message": "Low customer engagement - consider proactive outreach"
            })

        if dimensions.get("recency", 0) < 0.4:
            insights.append({
                "type": "alert",
                "dimension": "recency",
                "message": "No recent communication - immediate follow-up recommended"
            })

        if dimensions.get("value", 0) > 0.8 and dimensions.get("growth", 0) < 0.6:
            insights.append({
                "type": "opportunity",
                "dimension": "growth",
                "message": "High-value customer with expansion potential"
            })

        # Overall health insights
        if composite_score > 80:
            insights.append({
                "type": "positive",
                "dimension": "overall",
                "message": "Customer is highly engaged and healthy"
            })
        elif composite_score < 40:
            insights.append({
                "type": "critical",
                "dimension": "overall",
                "message": "Customer at high risk of churn - immediate intervention needed"
            })

        return insights

    def _assess_retention_risk(self, dimensions: Dict[str, float], composite_score: float) -> Dict[str, Any]:
        """Assess customer retention risk"""

        # Calculate churn probability based on health factors
        risk_factors = []

        if dimensions.get("engagement", 0) < 0.3:
            risk_factors.append("low_engagement")
        if dimensions.get("recency", 0) < 0.2:
            risk_factors.append("no_recent_contact")
        if dimensions.get("deal_performance", 0) < 0.5:
            risk_factors.append("poor_deal_history")

        # Base churn probability
        base_churn_prob = 0.1

        # Increase probability based on risk factors
        churn_probability = base_churn_prob + (len(risk_factors) * 0.2)

        # Adjust based on composite score
        if composite_score < 30:
            churn_probability += 0.3
        elif composite_score < 50:
            churn_probability += 0.2
        elif composite_score > 80:
            churn_probability -= 0.1

        # Normalize
        churn_probability = max(0.05, min(0.95, churn_probability))

        # Determine risk level
        if churn_probability > 0.8:
            risk_level = RetentionRisk.CRITICAL
        elif churn_probability > 0.5:
            risk_level = RetentionRisk.HIGH
        elif churn_probability > 0.2:
            risk_level = RetentionRisk.MEDIUM
        else:
            risk_level = RetentionRisk.LOW

        return {
            "risk_level": risk_level,
            "churn_probability": churn_probability,
            "risk_factors": risk_factors
        }

    async def _predict_health_trajectory(
        self,
        customer_data: Dict[str, Any],
        current_dimensions: Dict[str, float]
    ) -> Dict[str, Any]:
        """Predict future health trajectory"""

        # Simple trend-based prediction
        # In production, this would use ML models

        current_score = self._compute_composite_health_score(current_dimensions)

        # Predict 30, 60, 90 day scores based on trends
        predictions = {
            "30_days": max(0, current_score - 5),  # Slight decay
            "60_days": max(0, current_score - 10),
            "90_days": max(0, current_score - 15),
            "trend": "declining" if current_score < 60 else "stable",
            "confidence": 0.7
        }

        # Adjust predictions based on recent activity
        recent_activity = len([
            c for c in customer_data.get("communications", [])
            if c.created_at > datetime.utcnow() - timedelta(days=7)
        ])

        if recent_activity > 0:
            predictions["30_days"] += 5
            predictions["trend"] = "improving"

        return predictions

    async def _analyze_usage_patterns(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze customer usage patterns for expansion opportunities"""

        # Mock usage analysis - in production, integrate with product analytics
        usage_patterns = {
            "feature_adoption_rate": 0.6,
            "usage_frequency": "weekly",
            "power_user_indicators": ["api_usage", "advanced_features"],
            "growth_signals": ["team_expansion", "increased_usage"],
            "limitations_hit": ["user_limits", "feature_limits"]
        }

        return usage_patterns

    async def _analyze_expansion_potential(
        self,
        customer_data: Dict[str, Any],
        usage_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI-powered analysis of expansion potential"""

        # Calculate expansion potential score
        potential_score = 0.5  # Base score

        # Adjust based on usage patterns
        if usage_patterns.get("feature_adoption_rate", 0) > 0.7:
            potential_score += 0.2

        if "team_expansion" in usage_patterns.get("growth_signals", []):
            potential_score += 0.2

        if usage_patterns.get("limitations_hit"):
            potential_score += 0.1

        # Adjust based on customer value
        total_value = customer_data.get("total_value", 0)
        if total_value > 50000:
            potential_score += 0.1

        return {
            "potential_score": min(1.0, potential_score),
            "expansion_readiness": "high" if potential_score > 0.7 else "medium" if potential_score > 0.5 else "low",
            "confidence": 0.75,
            "key_indicators": usage_patterns.get("growth_signals", [])
        }

    async def _identify_specific_opportunities(
        self,
        customer_data: Dict[str, Any],
        expansion_analysis: Dict[str, Any],
        autonomy_level: int
    ) -> List[Dict[str, Any]]:
        """Identify specific expansion opportunities"""

        opportunities = []

        # Seat expansion
        if "team_expansion" in expansion_analysis.get("key_indicators", []):
            opportunities.append({
                "type": "seat_expansion",
                "description": "Additional user licenses",
                "estimated_value": 5000,
                "probability": 0.7,
                "timeline_days": 30
            })

        # Feature upgrade
        if expansion_analysis.get("potential_score", 0) > 0.6:
            opportunities.append({
                "type": "feature_upgrade",
                "description": "Premium feature access",
                "estimated_value": 10000,
                "probability": 0.5,
                "timeline_days": 60
            })

        # New product line
        current_value = customer_data.get("total_value", 0)
        if current_value > 25000:
            opportunities.append({
                "type": "cross_sell",
                "description": "Additional product modules",
                "estimated_value": 15000,
                "probability": 0.4,
                "timeline_days": 90
            })

        return opportunities

    def _prioritize_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize expansion opportunities by expected value"""

        for opp in opportunities:
            # Calculate expected value
            estimated_value = opp.get("estimated_value", 0)
            probability = opp.get("probability", 0.5)
            opp["expected_value"] = estimated_value * probability

            # Add priority score
            timeline_factor = 1.0 - (opp.get("timeline_days", 30) / 365)  # Favor shorter timelines
            opp["priority_score"] = opp["expected_value"] * timeline_factor

        # Sort by priority score
        return sorted(opportunities, key=lambda x: x.get("priority_score", 0), reverse=True)

    async def _create_expansion_strategy(
        self,
        opportunities: List[Dict[str, Any]],
        autonomy_level: int
    ) -> Dict[str, Any]:
        """Create expansion strategy"""

        if not opportunities:
            return {"immediate_actions": [], "timeline": "none"}

        top_opportunity = opportunities[0]

        strategy = {
            "primary_opportunity": top_opportunity,
            "approach": "consultative" if top_opportunity.get("estimated_value", 0) > 20000 else "self_service",
            "timeline": f"{top_opportunity.get('timeline_days', 30)} days",
            "immediate_actions": []
        }

        # Define actions based on autonomy level
        if autonomy_level >= 4:
            strategy["immediate_actions"] = [
                "auto_send_expansion_email",
                "schedule_success_review",
                "prepare_upgrade_proposal"
            ]
        elif autonomy_level >= 3:
            strategy["immediate_actions"] = [
                "send_expansion_email",
                "flag_for_account_review",
                "create_expansion_task"
            ]
        else:
            strategy["immediate_actions"] = [
                "notify_account_manager",
                "draft_expansion_proposal",
                "schedule_planning_meeting"
            ]

        return strategy

    async def _analyze_retention_factors(
        self,
        customer_data: Dict[str, Any],
        risk_level: str
    ) -> Dict[str, Any]:
        """Analyze factors affecting customer retention"""

        factors = {
            "satisfaction_indicators": [],
            "risk_factors": [],
            "retention_drivers": [],
            "intervention_opportunities": []
        }

        # Analyze communication patterns
        communications = customer_data.get("communications", [])
        recent_comms = [c for c in communications if c.created_at > datetime.utcnow() - timedelta(days=30)]

        if len(recent_comms) == 0:
            factors["risk_factors"].append("no_recent_communication")
            factors["intervention_opportunities"].append("proactive_outreach")

        # Analyze deal performance
        deals = customer_data.get("deals", [])
        if deals and all(deal.is_closed for deal in deals):
            if any(deal.is_won for deal in deals):
                factors["satisfaction_indicators"].append("successful_deal_history")
            else:
                factors["risk_factors"].append("poor_deal_history")

        # Value-based analysis
        total_value = customer_data.get("total_value", 0)
        if total_value > 50000:
            factors["retention_drivers"].append("high_investment")
        elif total_value < 5000:
            factors["risk_factors"].append("low_investment")

        return factors

    async def _design_retention_campaign(
        self,
        customer_data: Dict[str, Any],
        retention_analysis: Dict[str, Any],
        campaign_type: str,
        autonomy_level: int
    ) -> Dict[str, Any]:
        """Design targeted retention campaign"""

        risk_factors = retention_analysis.get("risk_factors", [])

        campaign = {
            "type": campaign_type,
            "duration_days": 14,
            "activities": [],
            "success_metrics": ["engagement_increase", "communication_response", "satisfaction_improvement"]
        }

        # Design activities based on risk factors
        if "no_recent_communication" in risk_factors:
            campaign["activities"].append({
                "type": "outreach_email",
                "timing": "immediate",
                "template": "check_in",
                "personalized": True
            })

        if "poor_deal_history" in risk_factors:
            campaign["activities"].append({
                "type": "success_consultation",
                "timing": "day_3",
                "template": "value_review",
                "include_discount": autonomy_level >= 3
            })

        # Add follow-up activities
        campaign["activities"].append({
            "type": "satisfaction_survey",
            "timing": "day_7",
            "template": "retention_survey"
        })

        return campaign

    async def _execute_campaign_activities(
        self,
        customer_id: UUID,
        campaign_design: Dict[str, Any],
        autonomy_level: int
    ) -> Dict[str, Any]:
        """Execute retention campaign activities"""

        campaign_id = f"retention_{customer_id}_{int(datetime.utcnow().timestamp())}"
        executed_activities = []

        activities = campaign_design.get("activities", [])

        for activity in activities:
            if activity.get("timing") == "immediate" and autonomy_level >= 3:
                # Execute immediate activities
                execution_result = await self._execute_activity(
                    customer_id, activity, autonomy_level
                )
                executed_activities.append(execution_result)

        return {
            "campaign_id": campaign_id,
            "executed_activities": executed_activities,
            "scheduled_activities": len(activities) - len(executed_activities)
        }

    async def _execute_activity(
        self,
        customer_id: UUID,
        activity: Dict[str, Any],
        autonomy_level: int
    ) -> Dict[str, Any]:
        """Execute a single campaign activity"""

        activity_type = activity.get("type")

        if activity_type == "outreach_email":
            # Send personalized outreach email
            result = await self.communication_service.send_email(
                to_email="customer@example.com",  # Would get from customer data
                subject="Checking in - How can we help?",
                content="Personalized retention email content...",
                lead_id=str(customer_id),
                autonomy_level=autonomy_level
            )

            return {
                "activity_type": activity_type,
                "status": "executed",
                "communication_id": result.get("communication_id"),
                "executed_at": datetime.utcnow().isoformat()
            }

        return {
            "activity_type": activity_type,
            "status": "scheduled",
            "reason": "Not immediately executable"
        }

    async def _setup_campaign_monitoring(
        self,
        customer_id: UUID,
        campaign_design: Dict[str, Any],
        campaign_execution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Setup monitoring for retention campaign"""

        success_metrics = campaign_design.get("success_metrics", [])

        monitoring = {
            "campaign_id": campaign_execution.get("campaign_id"),
            "tracked_metrics": success_metrics,
            "monitoring_duration_days": campaign_design.get("duration_days", 14),
            "alert_thresholds": {
                "no_response_days": 7,
                "negative_feedback": True
            }
        }

        return monitoring

    def _get_onboarding_customizations(self, customer_profile: Dict[str, Any]) -> List[str]:
        """Get onboarding customizations based on customer profile"""

        customizations = []

        priority_tier = customer_profile.get("priority_tier", "standard")
        if priority_tier == "high":
            customizations.extend(["dedicated_csm", "priority_support", "custom_training"])

        tech_level = customer_profile.get("technical_sophistication", "medium")
        if tech_level == "high":
            customizations.extend(["api_documentation", "developer_resources"])
        elif tech_level == "low":
            customizations.extend(["guided_setup", "extra_training_sessions"])

        return customizations

    def _define_success_criteria(self, customer_profile: Dict[str, Any]) -> List[str]:
        """Define success criteria for onboarding"""

        criteria = ["account_activation", "first_successful_use"]

        if customer_profile.get("company_size") == "enterprise":
            criteria.extend(["team_training_completion", "integration_setup"])

        if customer_profile.get("deal_value", 0) > 25000:
            criteria.append("roi_demonstration")

        return criteria

    async def _calculate_customer_metrics(
        self,
        date_from: datetime,
        date_to: datetime,
        segment: Optional[str]
    ) -> Dict[str, Any]:
        """Calculate customer metrics for the period"""

        # Mock metrics - in production, query actual data
        return {
            "total_customers": 245,
            "new_customers": 23,
            "churned_customers": 5,
            "net_retention_rate": 0.92,
            "gross_retention_rate": 0.95,
            "average_health_score": 72,
            "customers_at_risk": 18
        }

    async def _calculate_health_distribution(self) -> Dict[str, int]:
        """Calculate distribution of customer health scores"""

        # Mock distribution
        return {
            "excellent": 45,
            "good": 89,
            "fair": 67,
            "poor": 32,
            "critical": 12
        }

    async def _calculate_retention_metrics(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Calculate retention metrics"""

        return {
            "monthly_churn_rate": 0.05,
            "annual_churn_rate": 0.15,
            "customer_lifetime_value": 125000,
            "retention_cost_per_customer": 2500,
            "successful_interventions": 14
        }

    async def _calculate_expansion_metrics(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Calculate expansion metrics"""

        return {
            "expansion_rate": 0.25,
            "upsell_revenue": 450000,
            "cross_sell_revenue": 275000,
            "expansion_opportunities_identified": 67,
            "expansion_opportunities_closed": 18
        }

    async def _generate_predictive_insights(self, customer_metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate predictive insights"""

        insights = []

        churn_rate = customer_metrics.get("monthly_churn_rate", 0)
        if churn_rate > 0.03:
            insights.append({
                "type": "warning",
                "message": f"Churn rate ({churn_rate:.1%}) is above target - increase retention efforts"
            })

        health_score = customer_metrics.get("average_health_score", 0)
        if health_score > 75:
            insights.append({
                "type": "opportunity",
                "message": "High average health score indicates expansion opportunities"
            })

        return insights

    async def _publish_customer_event(self, subject: str, deal: Optional[Deal], event_data: Dict[str, Any]):
        """Publish customer success event to NATS"""

        try:
            nats_client = await get_nats_client()
            event_payload = {
                "deal_id": str(deal.id) if deal else None,
                "customer_id": event_data.get("customer_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "event_data": event_data
            }

            await nats_client.publish_event(subject, event_payload)

        except Exception as e:
            logger.warning("Failed to publish customer event", error=str(e))