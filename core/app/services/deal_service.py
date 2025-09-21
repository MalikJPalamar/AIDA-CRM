"""
AIDA-CRM Deal Service
Complete deal pipeline management and progression automation
"""

from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
import structlog

from ..models.deals import Deal, DealStage
from ..models.leads import Lead, LeadStatus
from ..models.communications import Communication
from ..services.ai_service import AIService
from ..services.nats_client import get_nats_client
from ..core.config import settings

logger = structlog.get_logger()


class DealService:
    """Service for deal pipeline management and automation"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()

    async def create_deal_from_lead(
        self,
        lead_id: UUID,
        title: Optional[str] = None,
        value: Optional[Decimal] = None,
        expected_close_date: Optional[datetime] = None,
        assigned_to: Optional[UUID] = None,
        autonomy_level: int = 1
    ) -> Dict[str, Any]:
        """Create a new deal from a qualified lead"""

        try:
            # Get lead information
            lead_query = select(Lead).where(Lead.id == lead_id)
            lead_result = await self.db.execute(lead_query)
            lead = lead_result.scalar_one_or_none()

            if not lead:
                raise ValueError(f"Lead {lead_id} not found")

            if lead.status != LeadStatus.QUALIFIED.value:
                raise ValueError(f"Lead must be qualified to create deal. Current status: {lead.status}")

            # AI-powered deal intelligence
            deal_intelligence = await self._analyze_deal_potential(lead, autonomy_level)

            # Generate deal details
            deal_title = title or self._generate_deal_title(lead, deal_intelligence)
            deal_value = value or deal_intelligence.get("estimated_value")
            close_date = expected_close_date or self._calculate_expected_close_date(
                deal_intelligence.get("urgency_score", 0.5)
            )

            # Create deal
            deal = Deal(
                lead_id=lead_id,
                title=deal_title,
                description=f"Deal created from qualified lead: {lead.email}",
                value=deal_value,
                currency="USD",
                stage=DealStage.QUALIFIED.value,
                probability=self._calculate_initial_probability(deal_intelligence),
                expected_close_date=close_date.date() if close_date else None,
                assigned_to=assigned_to or lead.assigned_to
            )

            # Save deal
            self.db.add(deal)
            await self.db.commit()
            await self.db.refresh(deal)

            # Update lead status
            lead.status = LeadStatus.CONVERTED.value
            await self.db.commit()

            # Publish events
            await self._publish_deal_event("deals.created", deal, deal_intelligence)

            # Determine next actions based on autonomy
            next_actions = await self._determine_deal_actions(deal, deal_intelligence, autonomy_level)

            result = {
                "deal_id": str(deal.id),
                "title": deal.title,
                "value": float(deal.value) if deal.value else None,
                "stage": deal.stage,
                "probability": deal.probability,
                "expected_close_date": deal.expected_close_date.isoformat() if deal.expected_close_date else None,
                "deal_intelligence": deal_intelligence,
                "next_actions": next_actions,
                "autonomy_level": autonomy_level
            }

            logger.info(
                "Deal created from lead",
                deal_id=str(deal.id),
                lead_id=str(lead_id),
                value=float(deal.value) if deal.value else None,
                stage=deal.stage
            )

            return result

        except Exception as e:
            await self.db.rollback()
            logger.error("Deal creation failed", lead_id=str(lead_id), error=str(e))
            raise

    async def progress_deal(
        self,
        deal_id: UUID,
        new_stage: str,
        reason: Optional[str] = None,
        autonomy_level: int = 1,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Progress deal to new stage with validation and automation"""

        try:
            # Get deal
            deal_query = select(Deal).where(Deal.id == deal_id)
            deal_result = await self.db.execute(deal_query)
            deal = deal_result.scalar_one_or_none()

            if not deal:
                raise ValueError(f"Deal {deal_id} not found")

            if deal.is_closed:
                raise ValueError(f"Cannot progress closed deal")

            # Validate stage transition
            old_stage = deal.stage
            stage_validation = self._validate_stage_transition(old_stage, new_stage)

            if not stage_validation["valid"]:
                raise ValueError(f"Invalid stage transition: {stage_validation['reason']}")

            # AI analysis for stage progression
            progression_analysis = await self._analyze_stage_progression(deal, new_stage, autonomy_level)

            # Autonomy-based progression control
            progression_decision = self._make_progression_decision(
                progression_analysis, autonomy_level, stage_validation
            )

            if not progression_decision["approved"]:
                return {
                    "deal_id": str(deal_id),
                    "status": "pending_approval",
                    "reason": progression_decision["reason"],
                    "requires_review": True,
                    "progression_analysis": progression_analysis
                }

            # Update deal
            deal.stage = new_stage
            deal.probability = self._update_probability_for_stage(new_stage, progression_analysis)

            # Auto-close if won/lost
            if new_stage in [DealStage.CLOSED_WON.value, DealStage.CLOSED_LOST.value]:
                deal.expected_close_date = datetime.utcnow().date()

            await self.db.commit()

            # Publish progression event
            await self._publish_deal_event("deals.progressed", deal, {
                "old_stage": old_stage,
                "new_stage": new_stage,
                "reason": reason,
                "progression_analysis": progression_analysis
            })

            # Generate next actions
            next_actions = await self._determine_stage_actions(deal, new_stage, autonomy_level)

            result = {
                "deal_id": str(deal_id),
                "old_stage": old_stage,
                "new_stage": new_stage,
                "probability": deal.probability,
                "status": "progressed",
                "progression_analysis": progression_analysis,
                "next_actions": next_actions,
                "autonomy_level": autonomy_level
            }

            logger.info(
                "Deal progressed",
                deal_id=str(deal_id),
                old_stage=old_stage,
                new_stage=new_stage,
                probability=deal.probability
            )

            return result

        except Exception as e:
            await self.db.rollback()
            logger.error("Deal progression failed", deal_id=str(deal_id), error=str(e))
            raise

    async def update_deal_value(
        self,
        deal_id: UUID,
        new_value: Decimal,
        reason: Optional[str] = None,
        autonomy_level: int = 1
    ) -> Dict[str, Any]:
        """Update deal value with AI validation"""

        try:
            # Get deal
            deal_query = select(Deal).where(Deal.id == deal_id)
            deal_result = await self.db.execute(deal_query)
            deal = deal_result.scalar_one_or_none()

            if not deal:
                raise ValueError(f"Deal {deal_id} not found")

            old_value = deal.value
            value_change = float(new_value - old_value) if old_value else float(new_value)
            change_percentage = (value_change / float(old_value)) * 100 if old_value else 0

            # AI validation for significant value changes
            if abs(change_percentage) > 25 and autonomy_level < 4:
                validation = await self._validate_value_change(deal, new_value, change_percentage)

                if not validation["approved"]:
                    return {
                        "deal_id": str(deal_id),
                        "status": "pending_approval",
                        "reason": f"Significant value change ({change_percentage:.1f}%) requires review",
                        "validation": validation,
                        "requires_review": True
                    }

            # Update deal value
            deal.value = new_value
            await self.db.commit()

            # Publish value change event
            await self._publish_deal_event("deals.value_updated", deal, {
                "old_value": float(old_value) if old_value else None,
                "new_value": float(new_value),
                "change_amount": value_change,
                "change_percentage": change_percentage,
                "reason": reason
            })

            result = {
                "deal_id": str(deal_id),
                "old_value": float(old_value) if old_value else None,
                "new_value": float(new_value),
                "change_amount": value_change,
                "change_percentage": change_percentage,
                "status": "updated"
            }

            logger.info(
                "Deal value updated",
                deal_id=str(deal_id),
                old_value=float(old_value) if old_value else None,
                new_value=float(new_value),
                change_percentage=change_percentage
            )

            return result

        except Exception as e:
            await self.db.rollback()
            logger.error("Deal value update failed", deal_id=str(deal_id), error=str(e))
            raise

    async def get_pipeline_analytics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        assigned_to: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get comprehensive pipeline analytics"""

        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=90)
            if not date_to:
                date_to = datetime.utcnow()

            # Base query with filters
            base_query = select(Deal).where(
                and_(Deal.created_at >= date_from, Deal.created_at <= date_to)
            )

            if assigned_to:
                base_query = base_query.where(Deal.assigned_to == assigned_to)

            # Get all deals
            deals_result = await self.db.execute(base_query)
            deals = deals_result.scalars().all()

            # Calculate analytics
            analytics = self._calculate_pipeline_metrics(deals)

            # Add forecasting
            forecast = await self._generate_pipeline_forecast(deals)

            # Stage analysis
            stage_analysis = self._analyze_stages(deals)

            # Performance metrics
            performance = self._calculate_performance_metrics(deals, date_from, date_to)

            result = {
                "period": {
                    "from": date_from.isoformat(),
                    "to": date_to.isoformat()
                },
                "summary": analytics,
                "forecast": forecast,
                "stage_analysis": stage_analysis,
                "performance": performance,
                "total_deals": len(deals)
            }

            logger.info(
                "Pipeline analytics generated",
                total_deals=len(deals),
                period_days=(date_to - date_from).days
            )

            return result

        except Exception as e:
            logger.error("Pipeline analytics failed", error=str(e))
            raise

    async def _analyze_deal_potential(self, lead: Lead, autonomy_level: int) -> Dict[str, Any]:
        """AI analysis of deal potential from lead data"""

        try:
            # Prepare lead data for analysis
            lead_data = {
                "email": lead.email,
                "company": lead.company,
                "source": lead.source,
                "qualification_score": float(lead.qualification_score) if lead.qualification_score else None,
                "utm_params": lead.utm_params,
                "custom_fields": lead.custom_fields
            }

            # AI-powered deal intelligence
            intelligence = await self.ai_service.analyze_lead_intent(lead_data)

            # Enhance with CRM-specific scoring
            estimated_value = self._estimate_deal_value(lead_data, intelligence)
            urgency_score = intelligence.get("urgency_level", "medium")
            deal_fit_score = self._calculate_deal_fit(lead_data)

            return {
                "estimated_value": estimated_value,
                "urgency_score": self._convert_urgency_to_score(urgency_score),
                "deal_fit_score": deal_fit_score,
                "ai_intent": intelligence,
                "confidence": 0.8 if autonomy_level >= 3 else 0.6
            }

        except Exception as e:
            logger.warning("Deal analysis failed", error=str(e))
            # Return safe defaults
            return {
                "estimated_value": Decimal("10000"),
                "urgency_score": 0.5,
                "deal_fit_score": 0.6,
                "ai_intent": {"intent_score": 0.5},
                "confidence": 0.3
            }

    def _generate_deal_title(self, lead: Lead, intelligence: Dict[str, Any]) -> str:
        """Generate descriptive deal title"""

        company = lead.company or "Unknown Company"
        source = lead.source.replace("_", " ").title()

        if intelligence.get("urgency_score", 0) > 0.7:
            urgency_prefix = "Hot Lead:"
        elif intelligence.get("deal_fit_score", 0) > 0.8:
            urgency_prefix = "High Value:"
        else:
            urgency_prefix = "Opportunity:"

        return f"{urgency_prefix} {company} ({source})"

    def _calculate_expected_close_date(self, urgency_score: float) -> datetime:
        """Calculate expected close date based on urgency"""

        if urgency_score > 0.8:
            days_to_close = 14
        elif urgency_score > 0.6:
            days_to_close = 30
        elif urgency_score > 0.4:
            days_to_close = 60
        else:
            days_to_close = 90

        return datetime.utcnow() + timedelta(days=days_to_close)

    def _calculate_initial_probability(self, intelligence: Dict[str, Any]) -> int:
        """Calculate initial deal probability"""

        base_probability = 20  # Base 20% for new qualified leads

        # Adjust based on intelligence factors
        intent_score = intelligence.get("ai_intent", {}).get("intent_score", 0.5)
        urgency_score = intelligence.get("urgency_score", 0.5)
        fit_score = intelligence.get("deal_fit_score", 0.5)

        # Weight the factors
        composite_score = (intent_score * 0.4) + (urgency_score * 0.3) + (fit_score * 0.3)

        # Convert to probability
        probability_boost = int(composite_score * 60)  # Up to 60% boost
        final_probability = min(base_probability + probability_boost, 95)

        return final_probability

    def _validate_stage_transition(self, old_stage: str, new_stage: str) -> Dict[str, Any]:
        """Validate if stage transition is allowed"""

        # Define allowed transitions
        allowed_transitions = {
            DealStage.PROSPECT.value: [DealStage.QUALIFIED.value, DealStage.CLOSED_LOST.value],
            DealStage.QUALIFIED.value: [DealStage.PROPOSAL.value, DealStage.CLOSED_LOST.value],
            DealStage.PROPOSAL.value: [DealStage.NEGOTIATION.value, DealStage.QUALIFIED.value, DealStage.CLOSED_LOST.value],
            DealStage.NEGOTIATION.value: [DealStage.CLOSED_WON.value, DealStage.PROPOSAL.value, DealStage.CLOSED_LOST.value],
            DealStage.CLOSED_WON.value: [],  # Terminal state
            DealStage.CLOSED_LOST.value: [DealStage.QUALIFIED.value]  # Can reopen
        }

        allowed = allowed_transitions.get(old_stage, [])

        if new_stage in allowed:
            return {"valid": True, "reason": "Valid transition"}
        else:
            return {
                "valid": False,
                "reason": f"Cannot transition from {old_stage} to {new_stage}. Allowed: {allowed}"
            }

    async def _analyze_stage_progression(self, deal: Deal, new_stage: str, autonomy_level: int) -> Dict[str, Any]:
        """AI analysis of stage progression validity"""

        try:
            # Get deal context
            deal_context = {
                "current_stage": deal.stage,
                "target_stage": new_stage,
                "value": float(deal.value) if deal.value else None,
                "probability": deal.probability,
                "days_in_current_stage": (datetime.utcnow() - deal.created_at).days,
                "communication_count": await self._get_communication_count(deal.id)
            }

            # Stage-specific analysis
            stage_risks = self._analyze_stage_risks(deal_context)
            readiness_score = self._calculate_stage_readiness(deal_context)

            return {
                "readiness_score": readiness_score,
                "stage_risks": stage_risks,
                "confidence": 0.8 if readiness_score > 0.7 else 0.5,
                "recommendations": self._generate_stage_recommendations(deal_context, readiness_score)
            }

        except Exception as e:
            logger.warning("Stage progression analysis failed", error=str(e))
            return {
                "readiness_score": 0.5,
                "stage_risks": ["Analysis unavailable"],
                "confidence": 0.3,
                "recommendations": ["Manual review recommended"]
            }

    def _make_progression_decision(
        self,
        analysis: Dict[str, Any],
        autonomy_level: int,
        validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make autonomous progression decision based on autonomy level"""

        if not validation["valid"]:
            return {"approved": False, "reason": validation["reason"]}

        readiness_score = analysis.get("readiness_score", 0.5)
        confidence = analysis.get("confidence", 0.5)

        # Autonomy-based thresholds
        thresholds = {
            1: {"readiness": 0.9, "confidence": 0.9},  # Very conservative
            2: {"readiness": 0.8, "confidence": 0.8},  # Conservative
            3: {"readiness": 0.7, "confidence": 0.7},  # Moderate
            4: {"readiness": 0.6, "confidence": 0.6},  # Aggressive
            5: {"readiness": 0.5, "confidence": 0.5},  # Very aggressive
        }

        threshold = thresholds.get(autonomy_level, thresholds[1])

        if readiness_score >= threshold["readiness"] and confidence >= threshold["confidence"]:
            return {
                "approved": True,
                "reason": f"Meets L{autonomy_level} progression criteria"
            }
        else:
            return {
                "approved": False,
                "reason": f"Below L{autonomy_level} thresholds (readiness: {readiness_score:.2f}, confidence: {confidence:.2f})"
            }

    def _update_probability_for_stage(self, stage: str, analysis: Dict[str, Any]) -> int:
        """Update deal probability based on stage and analysis"""

        # Base probabilities by stage
        stage_probabilities = {
            DealStage.PROSPECT.value: 10,
            DealStage.QUALIFIED.value: 25,
            DealStage.PROPOSAL.value: 50,
            DealStage.NEGOTIATION.value: 75,
            DealStage.CLOSED_WON.value: 100,
            DealStage.CLOSED_LOST.value: 0
        }

        base_prob = stage_probabilities.get(stage, 25)

        # Adjust based on readiness score
        readiness_score = analysis.get("readiness_score", 0.5)
        adjustment = int((readiness_score - 0.5) * 20)  # +/- 10%

        return max(0, min(100, base_prob + adjustment))

    async def _determine_deal_actions(
        self,
        deal: Deal,
        intelligence: Dict[str, Any],
        autonomy_level: int
    ) -> List[str]:
        """Determine next actions for new deal"""

        actions = []

        urgency_score = intelligence.get("urgency_score", 0.5)
        fit_score = intelligence.get("deal_fit_score", 0.5)

        if urgency_score > 0.8:
            if autonomy_level >= 4:
                actions.extend(["auto_schedule_demo", "send_priority_alert"])
            else:
                actions.extend(["schedule_demo", "notify_sales_manager"])

        if fit_score > 0.8:
            actions.append("add_to_high_value_pipeline")

        # Standard actions
        if autonomy_level >= 3:
            actions.extend(["send_deal_welcome_email", "create_follow_up_tasks"])
        else:
            actions.extend(["draft_welcome_email", "suggest_follow_up_tasks"])

        return actions

    async def _determine_stage_actions(
        self,
        deal: Deal,
        stage: str,
        autonomy_level: int
    ) -> List[str]:
        """Determine next actions based on deal stage"""

        actions = []

        stage_actions = {
            DealStage.QUALIFIED.value: ["send_qualification_summary", "schedule_needs_assessment"],
            DealStage.PROPOSAL.value: ["prepare_proposal", "schedule_presentation"],
            DealStage.NEGOTIATION.value: ["review_contract_terms", "prepare_closing_materials"],
            DealStage.CLOSED_WON.value: ["initiate_onboarding", "send_welcome_package"],
            DealStage.CLOSED_LOST.value: ["conduct_loss_analysis", "add_to_nurture_campaign"]
        }

        base_actions = stage_actions.get(stage, [])

        if autonomy_level >= 4:
            # Auto-execute actions
            actions.extend([f"auto_{action}" for action in base_actions])
        elif autonomy_level >= 3:
            # Execute with notification
            actions.extend(base_actions)
        else:
            # Suggest actions
            actions.extend([f"suggest_{action}" for action in base_actions])

        return actions

    def _estimate_deal_value(self, lead_data: Dict[str, Any], intelligence: Dict[str, Any]) -> Decimal:
        """Estimate deal value based on lead data and AI intelligence"""

        # Base value by source
        source_values = {
            "demo_request": 25000,
            "pricing_page": 20000,
            "enterprise_form": 50000,
            "referral": 30000,
            "webinar": 15000,
            "content_download": 10000,
            "website": 12000
        }

        source = lead_data.get("source", "website")
        base_value = source_values.get(source, 12000)

        # Adjust based on company indicators
        company = lead_data.get("company", "").lower()
        if any(indicator in company for indicator in ["enterprise", "corp", "inc", "international"]):
            base_value *= 2

        # Adjust based on AI intent
        intent_score = intelligence.get("intent_score", 0.5)
        intent_multiplier = 0.5 + (intent_score * 1.5)  # 0.5x to 2x

        final_value = int(base_value * intent_multiplier)
        return Decimal(str(final_value))

    def _convert_urgency_to_score(self, urgency_level: str) -> float:
        """Convert urgency level to numeric score"""
        urgency_map = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.9
        }
        return urgency_map.get(urgency_level, 0.5)

    def _calculate_deal_fit(self, lead_data: Dict[str, Any]) -> float:
        """Calculate how well the lead fits ideal customer profile"""

        score = 0.5  # Base score

        # Company presence
        if lead_data.get("company"):
            score += 0.2

        # High-value sources
        high_value_sources = ["demo_request", "enterprise_form", "referral"]
        if lead_data.get("source") in high_value_sources:
            score += 0.2

        # Qualification score
        qual_score = lead_data.get("qualification_score")
        if qual_score and qual_score > 0.7:
            score += 0.1

        return min(score, 1.0)

    async def _get_communication_count(self, deal_id: UUID) -> int:
        """Get number of communications for a deal"""
        try:
            query = select(func.count(Communication.id)).where(Communication.deal_id == deal_id)
            result = await self.db.execute(query)
            return result.scalar() or 0
        except Exception:
            return 0

    def _analyze_stage_risks(self, deal_context: Dict[str, Any]) -> List[str]:
        """Analyze risks for stage progression"""
        risks = []

        days_in_stage = deal_context.get("days_in_current_stage", 0)
        comm_count = deal_context.get("communication_count", 0)

        if days_in_stage > 30:
            risks.append("Deal has been in current stage for extended period")

        if comm_count < 2:
            risks.append("Low communication volume with prospect")

        current_stage = deal_context.get("current_stage")
        if current_stage == DealStage.PROPOSAL.value and comm_count < 5:
            risks.append("Insufficient communication before proposal stage")

        return risks

    def _calculate_stage_readiness(self, deal_context: Dict[str, Any]) -> float:
        """Calculate readiness score for stage progression"""
        score = 0.5  # Base readiness

        # Communication factor
        comm_count = deal_context.get("communication_count", 0)
        if comm_count >= 3:
            score += 0.2
        elif comm_count >= 1:
            score += 0.1

        # Time factor (not too fast, not too slow)
        days_in_stage = deal_context.get("days_in_current_stage", 0)
        if 7 <= days_in_stage <= 21:  # Sweet spot
            score += 0.2
        elif 3 <= days_in_stage <= 30:  # Acceptable
            score += 0.1

        # Probability factor
        probability = deal_context.get("probability", 0)
        if probability >= 60:
            score += 0.1

        return min(score, 1.0)

    def _generate_stage_recommendations(self, deal_context: Dict[str, Any], readiness_score: float) -> List[str]:
        """Generate recommendations for stage progression"""
        recommendations = []

        if readiness_score < 0.6:
            recommendations.append("Increase communication with prospect before advancing")

        comm_count = deal_context.get("communication_count", 0)
        if comm_count < 2:
            recommendations.append("Schedule discovery call to understand needs")

        days_in_stage = deal_context.get("days_in_current_stage", 0)
        if days_in_stage > 45:
            recommendations.append("Review deal status and re-qualify opportunity")

        return recommendations

    async def _validate_value_change(self, deal: Deal, new_value: Decimal, change_percentage: float) -> Dict[str, Any]:
        """AI validation of significant value changes"""
        # In production, this would use AI to validate based on:
        # - Historical patterns
        # - Company size indicators
        # - Market benchmarks
        # - Deal progression stage

        if abs(change_percentage) > 50:
            return {
                "approved": False,
                "reason": f"Value change of {change_percentage:.1f}% requires manual approval",
                "confidence": 0.9
            }

        return {
            "approved": True,
            "reason": "Value change within acceptable range",
            "confidence": 0.7
        }

    async def _publish_deal_event(self, subject: str, deal: Deal, event_data: Dict[str, Any]):
        """Publish deal event to NATS"""
        try:
            nats_client = await get_nats_client()
            event_payload = {
                "deal_id": str(deal.id),
                "lead_id": str(deal.lead_id) if deal.lead_id else None,
                "title": deal.title,
                "stage": deal.stage,
                "value": float(deal.value) if deal.value else None,
                "probability": deal.probability,
                "event_data": event_data
            }

            await nats_client.publish_event(subject, event_payload)

        except Exception as e:
            logger.warning("Failed to publish deal event", error=str(e))

    def _calculate_pipeline_metrics(self, deals: List[Deal]) -> Dict[str, Any]:
        """Calculate comprehensive pipeline metrics"""
        if not deals:
            return {}

        total_value = sum(float(deal.value) for deal in deals if deal.value)
        weighted_value = sum(
            float(deal.value) * (deal.probability / 100)
            for deal in deals if deal.value and not deal.is_closed
        )

        won_deals = [deal for deal in deals if deal.is_won]
        lost_deals = [deal for deal in deals if deal.is_lost]
        active_deals = [deal for deal in deals if not deal.is_closed]

        won_value = sum(float(deal.value) for deal in won_deals if deal.value)
        lost_value = sum(float(deal.value) for deal in lost_deals if deal.value)

        return {
            "total_deals": len(deals),
            "active_deals": len(active_deals),
            "won_deals": len(won_deals),
            "lost_deals": len(lost_deals),
            "total_value": total_value,
            "weighted_value": weighted_value,
            "won_value": won_value,
            "lost_value": lost_value,
            "win_rate": len(won_deals) / len(deals) if deals else 0,
            "average_deal_value": total_value / len(deals) if deals else 0,
            "average_probability": sum(deal.probability for deal in active_deals) / len(active_deals) if active_deals else 0
        }

    async def _generate_pipeline_forecast(self, deals: List[Deal]) -> Dict[str, Any]:
        """Generate pipeline forecast"""
        active_deals = [deal for deal in deals if not deal.is_closed]

        # Simple forecast based on probability
        forecast_30_days = sum(
            float(deal.value) * (deal.probability / 100) * 0.3
            for deal in active_deals
            if deal.value and deal.expected_close_date and
            deal.expected_close_date <= (datetime.utcnow() + timedelta(days=30)).date()
        )

        forecast_90_days = sum(
            float(deal.value) * (deal.probability / 100) * 0.7
            for deal in active_deals
            if deal.value and deal.expected_close_date and
            deal.expected_close_date <= (datetime.utcnow() + timedelta(days=90)).date()
        )

        return {
            "forecast_30_days": forecast_30_days,
            "forecast_90_days": forecast_90_days,
            "confidence": 0.7,
            "methodology": "probability_weighted"
        }

    def _analyze_stages(self, deals: List[Deal]) -> Dict[str, Any]:
        """Analyze deals by stage"""
        stage_analysis = {}

        for stage in DealStage:
            stage_deals = [deal for deal in deals if deal.stage == stage.value]
            stage_value = sum(float(deal.value) for deal in stage_deals if deal.value)

            stage_analysis[stage.value] = {
                "count": len(stage_deals),
                "value": stage_value,
                "average_value": stage_value / len(stage_deals) if stage_deals else 0,
                "average_probability": sum(deal.probability for deal in stage_deals) / len(stage_deals) if stage_deals else 0
            }

        return stage_analysis

    def _calculate_performance_metrics(self, deals: List[Deal], date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        """Calculate performance metrics for the period"""
        period_days = (date_to - date_from).days

        # Velocity (deals created per day)
        velocity = len(deals) / period_days if period_days > 0 else 0

        # Average time in pipeline (for closed deals)
        closed_deals = [deal for deal in deals if deal.is_closed]
        if closed_deals:
            avg_cycle_time = sum(
                (deal.updated_at - deal.created_at).days for deal in closed_deals
            ) / len(closed_deals)
        else:
            avg_cycle_time = 0

        return {
            "velocity_deals_per_day": velocity,
            "average_cycle_time_days": avg_cycle_time,
            "period_days": period_days
        }