"""
AIDA-CRM Autonomy Engine
Advanced L4-L5 autonomy with intelligent decision workflows
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import structlog

from ..models.users import User
from ..models.leads import Lead
from ..models.deals import Deal
from ..models.communications import Communication
from ..services.ai_service import AIService
from ..services.nats_client import get_nats_client
from ..core.config import settings

logger = structlog.get_logger()


class AutonomyLevel(int, Enum):
    """Autonomy levels with specific capabilities"""
    L1_DRAFT = 1      # Draft-only, human executes
    L2_ASSISTED = 2   # System performs with human approval
    L3_SUPERVISED = 3 # System acts with human oversight
    L4_DELEGATED = 4  # System operates within defined boundaries
    L5_AUTONOMOUS = 5 # Full automation with human-on-the-loop


class DecisionType(str, Enum):
    """Types of autonomous decisions"""
    LEAD_QUALIFICATION = "lead_qualification"
    DEAL_PROGRESSION = "deal_progression"
    COMMUNICATION_SEND = "communication_send"
    VALUE_UPDATE = "value_update"
    ASSIGNMENT = "assignment"
    ESCALATION = "escalation"


class ConfidenceLevel(str, Enum):
    """Confidence levels for decisions"""
    VERY_LOW = "very_low"    # < 0.3
    LOW = "low"              # 0.3 - 0.5
    MEDIUM = "medium"        # 0.5 - 0.7
    HIGH = "high"            # 0.7 - 0.9
    VERY_HIGH = "very_high"  # > 0.9


class AutonomyEngine:
    """Advanced autonomy engine for intelligent CRM automation"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()

    async def make_autonomous_decision(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        autonomy_level: int,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make an autonomous decision based on context and autonomy level"""

        try:
            # Analyze decision context
            analysis = await self._analyze_decision_context(decision_type, context)

            # Calculate confidence score
            confidence = self._calculate_confidence_score(analysis, context)

            # Check autonomy permissions
            permissions = await self._check_autonomy_permissions(
                decision_type, autonomy_level, confidence, user_id
            )

            # Make decision based on autonomy level
            decision = await self._execute_autonomous_decision(
                decision_type, context, analysis, confidence, permissions
            )

            # Log decision for audit
            await self._log_autonomous_decision(
                decision_type, context, decision, confidence, autonomy_level
            )

            # Escalate if needed
            if decision.get("requires_escalation"):
                await self._escalate_decision(decision_type, context, decision, user_id)

            logger.info(
                "Autonomous decision made",
                decision_type=decision_type.value,
                autonomy_level=autonomy_level,
                confidence=confidence,
                decision_status=decision.get("status")
            )

            return decision

        except Exception as e:
            logger.error("Autonomous decision failed", decision_type=decision_type.value, error=str(e))
            # Return safe fallback
            return {
                "status": "error",
                "decision": "escalate_to_human",
                "reason": f"Decision engine error: {str(e)}",
                "requires_escalation": True,
                "confidence": 0.0
            }

    async def configure_autonomy_settings(
        self,
        user_id: str,
        process: str,
        level: int,
        confidence_threshold: float = 0.8,
        custom_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Configure autonomy settings for a user and process"""

        try:
            # Validate autonomy level
            if level not in [1, 2, 3, 4, 5]:
                raise ValueError(f"Invalid autonomy level: {level}")

            # Validate confidence threshold
            if not 0.1 <= confidence_threshold <= 1.0:
                raise ValueError(f"Invalid confidence threshold: {confidence_threshold}")

            # Get or create autonomy configuration
            config = await self._get_or_create_autonomy_config(
                user_id, process, level, confidence_threshold, custom_rules
            )

            # Validate configuration against business rules
            validation = self._validate_autonomy_config(config)

            if not validation["valid"]:
                raise ValueError(f"Invalid configuration: {validation['reason']}")

            result = {
                "user_id": user_id,
                "process": process,
                "level": level,
                "confidence_threshold": confidence_threshold,
                "custom_rules": custom_rules,
                "status": "configured",
                "effective_immediately": True
            }

            logger.info(
                "Autonomy settings configured",
                user_id=user_id,
                process=process,
                level=level,
                threshold=confidence_threshold
            )

            return result

        except Exception as e:
            logger.error("Autonomy configuration failed", error=str(e))
            raise

    async def get_autonomy_performance(
        self,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get autonomy performance metrics and recommendations"""

        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()

            # Get autonomy decisions and outcomes
            decisions = await self._get_autonomy_decisions(user_id, date_from, date_to)

            # Calculate performance metrics
            metrics = self._calculate_autonomy_metrics(decisions)

            # Generate insights and recommendations
            insights = await self._generate_autonomy_insights(decisions, metrics)

            # Suggest autonomy adjustments
            adjustments = self._suggest_autonomy_adjustments(metrics, insights)

            result = {
                "period": {
                    "from": date_from.isoformat(),
                    "to": date_to.isoformat()
                },
                "metrics": metrics,
                "insights": insights,
                "recommendations": adjustments,
                "total_decisions": len(decisions)
            }

            return result

        except Exception as e:
            logger.error("Autonomy performance analysis failed", error=str(e))
            raise

    async def _analyze_decision_context(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the context for autonomous decision making"""

        analysis = {
            "decision_type": decision_type.value,
            "context_completeness": self._assess_context_completeness(context),
            "historical_patterns": await self._analyze_historical_patterns(decision_type, context),
            "risk_factors": self._identify_risk_factors(decision_type, context),
            "business_impact": self._assess_business_impact(decision_type, context)
        }

        # Decision-specific analysis
        if decision_type == DecisionType.LEAD_QUALIFICATION:
            analysis.update(await self._analyze_qualification_context(context))
        elif decision_type == DecisionType.DEAL_PROGRESSION:
            analysis.update(await self._analyze_progression_context(context))
        elif decision_type == DecisionType.COMMUNICATION_SEND:
            analysis.update(await self._analyze_communication_context(context))

        return analysis

    def _calculate_confidence_score(
        self,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for the decision"""

        # Base confidence from context completeness
        base_confidence = analysis.get("context_completeness", 0.5)

        # Adjust based on historical patterns
        historical_confidence = analysis.get("historical_patterns", {}).get("confidence", 0.5)

        # Risk adjustment
        risk_factors = len(analysis.get("risk_factors", []))
        risk_penalty = min(risk_factors * 0.1, 0.3)

        # Business impact adjustment
        impact_score = analysis.get("business_impact", {}).get("score", 0.5)

        # Weighted combination
        confidence = (
            base_confidence * 0.3 +
            historical_confidence * 0.3 +
            impact_score * 0.2 +
            (1.0 - risk_penalty) * 0.2
        )

        return max(0.1, min(1.0, confidence))

    async def _check_autonomy_permissions(
        self,
        decision_type: DecisionType,
        autonomy_level: int,
        confidence: float,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Check if autonomy level permits this decision"""

        # Get user's autonomy configuration
        config = await self._get_user_autonomy_config(user_id, decision_type.value)

        # Check level permissions
        level_threshold = config.get("level", 1)
        confidence_threshold = config.get("confidence_threshold", 0.8)

        permissions = {
            "level_permitted": autonomy_level >= level_threshold,
            "confidence_met": confidence >= confidence_threshold,
            "custom_rules_passed": self._check_custom_rules(config, decision_type, confidence),
            "time_restrictions": self._check_time_restrictions(config),
            "value_limits": self._check_value_limits(config, decision_type)
        }

        permissions["all_checks_passed"] = all(permissions.values())

        return permissions

    async def _execute_autonomous_decision(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        analysis: Dict[str, Any],
        confidence: float,
        permissions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the autonomous decision based on analysis"""

        if not permissions["all_checks_passed"]:
            return {
                "status": "blocked",
                "decision": "escalate_to_human",
                "reason": "Insufficient autonomy permissions",
                "permissions": permissions,
                "requires_escalation": True
            }

        # Execute decision based on type
        if decision_type == DecisionType.LEAD_QUALIFICATION:
            return await self._execute_qualification_decision(context, analysis, confidence)
        elif decision_type == DecisionType.DEAL_PROGRESSION:
            return await self._execute_progression_decision(context, analysis, confidence)
        elif decision_type == DecisionType.COMMUNICATION_SEND:
            return await self._execute_communication_decision(context, analysis, confidence)
        else:
            return {
                "status": "not_implemented",
                "decision": "escalate_to_human",
                "reason": f"Decision type {decision_type.value} not implemented",
                "requires_escalation": True
            }

    async def _execute_qualification_decision(
        self,
        context: Dict[str, Any],
        analysis: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """Execute autonomous lead qualification decision"""

        qualification_score = context.get("qualification_score", 0.5)
        lead_data = context.get("lead_data", {})

        # Decision thresholds based on confidence
        if confidence > 0.8:
            qualify_threshold = 0.6
            reject_threshold = 0.3
        elif confidence > 0.6:
            qualify_threshold = 0.7
            reject_threshold = 0.2
        else:
            qualify_threshold = 0.8
            reject_threshold = 0.15

        if qualification_score >= qualify_threshold:
            decision = "qualify"
            next_actions = ["create_deal", "assign_to_sales", "send_welcome_email"]
        elif qualification_score <= reject_threshold:
            decision = "reject"
            next_actions = ["add_to_nurture", "tag_for_future_review"]
        else:
            decision = "review"
            next_actions = ["manual_qualification", "request_more_info"]

        return {
            "status": "executed",
            "decision": decision,
            "qualification_score": qualification_score,
            "confidence": confidence,
            "next_actions": next_actions,
            "requires_escalation": decision == "review" and confidence < 0.7
        }

    async def _execute_progression_decision(
        self,
        context: Dict[str, Any],
        analysis: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """Execute autonomous deal progression decision"""

        current_stage = context.get("current_stage")
        proposed_stage = context.get("proposed_stage")
        deal_data = context.get("deal_data", {})

        # Stage progression rules
        progression_confidence = analysis.get("progression_readiness", 0.5)
        risk_score = len(analysis.get("risk_factors", [])) / 10  # Normalize

        if progression_confidence >= 0.8 and risk_score < 0.3:
            decision = "approve_progression"
        elif progression_confidence >= 0.6 and risk_score < 0.5:
            decision = "approve_with_conditions"
        else:
            decision = "require_review"

        return {
            "status": "executed",
            "decision": decision,
            "from_stage": current_stage,
            "to_stage": proposed_stage,
            "progression_confidence": progression_confidence,
            "risk_score": risk_score,
            "confidence": confidence,
            "requires_escalation": decision == "require_review"
        }

    async def _execute_communication_decision(
        self,
        context: Dict[str, Any],
        analysis: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """Execute autonomous communication decision"""

        communication_type = context.get("type")
        recipient_data = context.get("recipient_data", {})
        content_score = analysis.get("content_quality", 0.5)

        # Communication approval rules
        if confidence > 0.8 and content_score > 0.7:
            decision = "send_immediately"
        elif confidence > 0.6 and content_score > 0.5:
            decision = "send_with_tracking"
        else:
            decision = "require_approval"

        return {
            "status": "executed",
            "decision": decision,
            "communication_type": communication_type,
            "content_score": content_score,
            "confidence": confidence,
            "requires_escalation": decision == "require_approval"
        }

    def _assess_context_completeness(self, context: Dict[str, Any]) -> float:
        """Assess how complete the decision context is"""

        required_fields = ["id", "type", "data"]
        optional_fields = ["user_id", "timestamp", "metadata"]

        completeness = 0.0

        # Check required fields
        for field in required_fields:
            if field in context and context[field] is not None:
                completeness += 0.5 / len(required_fields)

        # Check optional fields
        for field in optional_fields:
            if field in context and context[field] is not None:
                completeness += 0.5 / len(optional_fields)

        return min(1.0, completeness)

    async def _analyze_historical_patterns(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze historical patterns for similar decisions"""

        try:
            # In a full implementation, this would query historical decisions
            # For now, return mock analysis
            return {
                "similar_decisions": 25,
                "success_rate": 0.85,
                "average_confidence": 0.75,
                "confidence": 0.8
            }

        except Exception as e:
            logger.warning("Historical pattern analysis failed", error=str(e))
            return {
                "similar_decisions": 0,
                "success_rate": 0.5,
                "average_confidence": 0.5,
                "confidence": 0.3
            }

    def _identify_risk_factors(self, decision_type: DecisionType, context: Dict[str, Any]) -> List[str]:
        """Identify risk factors for the decision"""

        risks = []

        # General risk factors
        if context.get("value") and float(context["value"]) > 50000:
            risks.append("High value transaction")

        if context.get("urgency") == "high":
            risks.append("High urgency request")

        # Decision-specific risks
        if decision_type == DecisionType.DEAL_PROGRESSION:
            deal_age = context.get("deal_age_days", 0)
            if deal_age > 90:
                risks.append("Stale deal progression")

        if decision_type == DecisionType.COMMUNICATION_SEND:
            if context.get("recipient_count", 1) > 100:
                risks.append("Bulk communication")

        return risks

    def _assess_business_impact(self, decision_type: DecisionType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the business impact of the decision"""

        # Calculate impact score based on various factors
        impact_score = 0.5  # Base score

        # Financial impact
        value = context.get("value", 0)
        if value:
            if float(value) > 100000:
                impact_score += 0.3
            elif float(value) > 25000:
                impact_score += 0.2
            elif float(value) > 5000:
                impact_score += 0.1

        # Customer impact
        if context.get("customer_tier") == "enterprise":
            impact_score += 0.2

        # Strategic impact
        if context.get("strategic_account"):
            impact_score += 0.1

        return {
            "score": min(1.0, impact_score),
            "financial_impact": value,
            "customer_tier": context.get("customer_tier", "standard"),
            "strategic_importance": context.get("strategic_account", False)
        }

    async def _analyze_qualification_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze context specific to lead qualification"""

        lead_data = context.get("lead_data", {})

        return {
            "data_completeness": len([v for v in lead_data.values() if v]) / max(len(lead_data), 1),
            "source_quality": self._assess_source_quality(lead_data.get("source")),
            "engagement_signals": self._count_engagement_signals(lead_data)
        }

    async def _analyze_progression_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze context specific to deal progression"""

        deal_data = context.get("deal_data", {})

        return {
            "progression_readiness": 0.7,  # Mock - would calculate based on activities
            "stage_velocity": self._calculate_stage_velocity(deal_data),
            "communication_frequency": await self._get_communication_frequency(deal_data.get("id"))
        }

    async def _analyze_communication_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze context specific to communication decisions"""

        return {
            "content_quality": 0.8,  # Mock - would use AI to analyze content
            "timing_appropriateness": self._assess_timing(context),
            "personalization_level": self._assess_personalization(context)
        }

    def _assess_source_quality(self, source: Optional[str]) -> float:
        """Assess the quality of the lead source"""

        if not source:
            return 0.3

        quality_map = {
            "referral": 0.9,
            "demo_request": 0.8,
            "enterprise_form": 0.8,
            "pricing_page": 0.7,
            "webinar": 0.6,
            "content_download": 0.5,
            "social_media": 0.4,
            "web": 0.3
        }

        return quality_map.get(source.lower(), 0.3)

    def _count_engagement_signals(self, lead_data: Dict[str, Any]) -> int:
        """Count engagement signals in lead data"""

        signals = 0

        if lead_data.get("phone"):
            signals += 1
        if lead_data.get("company"):
            signals += 1
        if lead_data.get("utm_params"):
            signals += 1
        if lead_data.get("page_views", 0) > 3:
            signals += 1

        return signals

    def _calculate_stage_velocity(self, deal_data: Dict[str, Any]) -> float:
        """Calculate how quickly deal is progressing through stages"""

        # Mock calculation - would use actual stage history
        return 0.7

    async def _get_communication_frequency(self, deal_id: Optional[str]) -> float:
        """Get communication frequency for deal"""

        if not deal_id:
            return 0.3

        try:
            # Query communication count
            query = select(func.count(Communication.id)).where(Communication.deal_id == deal_id)
            result = await self.db.execute(query)
            comm_count = result.scalar() or 0

            # Normalize to 0-1 scale
            return min(1.0, comm_count / 10)

        except Exception:
            return 0.3

    def _assess_timing(self, context: Dict[str, Any]) -> float:
        """Assess if timing is appropriate for communication"""

        current_hour = datetime.now().hour

        # Business hours get higher score
        if 9 <= current_hour <= 17:
            return 0.8
        elif 8 <= current_hour <= 19:
            return 0.6
        else:
            return 0.3

    def _assess_personalization(self, context: Dict[str, Any]) -> float:
        """Assess level of personalization in communication"""

        personalization_data = context.get("personalization_data", {})

        if not personalization_data:
            return 0.3

        # Count personalization elements
        elements = len([v for v in personalization_data.values() if v])
        return min(1.0, elements / 5)  # Assume 5 is highly personalized

    async def _get_user_autonomy_config(self, user_id: Optional[str], process: str) -> Dict[str, Any]:
        """Get user's autonomy configuration for a process"""

        # Default configuration
        default_config = {
            "level": 1,
            "confidence_threshold": 0.8,
            "custom_rules": {},
            "time_restrictions": {},
            "value_limits": {}
        }

        if not user_id:
            return default_config

        try:
            # In a full implementation, query autonomy_configs table
            # For now, return enhanced defaults
            return {
                "level": 3,  # Moderate autonomy
                "confidence_threshold": 0.7,
                "custom_rules": {},
                "time_restrictions": {"business_hours_only": False},
                "value_limits": {"max_deal_value": 100000}
            }

        except Exception:
            return default_config

    def _check_custom_rules(
        self,
        config: Dict[str, Any],
        decision_type: DecisionType,
        confidence: float
    ) -> bool:
        """Check custom autonomy rules"""

        custom_rules = config.get("custom_rules", {})

        # If no custom rules, pass by default
        if not custom_rules:
            return True

        # Check decision-specific rules
        decision_rules = custom_rules.get(decision_type.value, {})

        # Check minimum confidence rule
        min_confidence = decision_rules.get("min_confidence")
        if min_confidence and confidence < min_confidence:
            return False

        return True

    def _check_time_restrictions(self, config: Dict[str, Any]) -> bool:
        """Check time-based restrictions"""

        time_restrictions = config.get("time_restrictions", {})

        if time_restrictions.get("business_hours_only"):
            current_hour = datetime.now().hour
            if not (9 <= current_hour <= 17):
                return False

        return True

    def _check_value_limits(self, config: Dict[str, Any], decision_type: DecisionType) -> bool:
        """Check value-based limits"""

        value_limits = config.get("value_limits", {})

        # Check deal value limits for deal-related decisions
        if decision_type in [DecisionType.DEAL_PROGRESSION, DecisionType.VALUE_UPDATE]:
            max_deal_value = value_limits.get("max_deal_value")
            if max_deal_value:
                # This would check actual deal value from context
                # For now, assume check passes
                pass

        return True

    async def _log_autonomous_decision(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        confidence: float,
        autonomy_level: int
    ):
        """Log autonomous decision for audit and learning"""

        try:
            # In a full implementation, save to audit table
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "decision_type": decision_type.value,
                "autonomy_level": autonomy_level,
                "confidence": confidence,
                "decision": decision.get("decision"),
                "status": decision.get("status"),
                "context_id": context.get("id"),
                "requires_escalation": decision.get("requires_escalation", False)
            }

            logger.info("Autonomous decision logged", **log_entry)

        except Exception as e:
            logger.warning("Failed to log autonomous decision", error=str(e))

    async def _escalate_decision(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        user_id: Optional[str]
    ):
        """Escalate decision to human review"""

        try:
            # Publish escalation event
            nats_client = await get_nats_client()
            escalation_data = {
                "decision_type": decision_type.value,
                "context": context,
                "decision": decision,
                "escalated_to": user_id,
                "escalation_reason": decision.get("reason"),
                "priority": "high" if decision.get("high_value") else "medium"
            }

            await nats_client.publish_event("autonomy.escalation", escalation_data)

            logger.info(
                "Decision escalated",
                decision_type=decision_type.value,
                escalated_to=user_id,
                reason=decision.get("reason")
            )

        except Exception as e:
            logger.warning("Failed to escalate decision", error=str(e))

    async def _get_or_create_autonomy_config(
        self,
        user_id: str,
        process: str,
        level: int,
        confidence_threshold: float,
        custom_rules: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get or create autonomy configuration"""

        # In a full implementation, this would interact with autonomy_configs table
        return {
            "user_id": user_id,
            "process": process,
            "level": level,
            "confidence_threshold": confidence_threshold,
            "custom_rules": custom_rules or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    def _validate_autonomy_config(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """Validate autonomy configuration"""

        level = config.get("level", 1)
        confidence_threshold = config.get("confidence_threshold", 0.8)

        # Business rules validation
        if level >= 4 and confidence_threshold < 0.7:
            return {
                "valid": False,
                "reason": "High autonomy levels require higher confidence thresholds"
            }

        if level == 5 and confidence_threshold < 0.8:
            return {
                "valid": False,
                "reason": "L5 autonomy requires minimum 0.8 confidence threshold"
            }

        return {"valid": True, "reason": "Configuration is valid"}

    async def _get_autonomy_decisions(
        self,
        user_id: Optional[str],
        date_from: datetime,
        date_to: datetime
    ) -> List[Dict[str, Any]]:
        """Get autonomy decisions for performance analysis"""

        # In a full implementation, query decision audit table
        # For now, return mock data
        return [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "decision_type": "lead_qualification",
                "autonomy_level": 3,
                "confidence": 0.85,
                "decision": "qualify",
                "outcome": "success",
                "human_override": False
            }
            # ... more decisions
        ]

    def _calculate_autonomy_metrics(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics for autonomy decisions"""

        if not decisions:
            return {}

        successful_decisions = len([d for d in decisions if d.get("outcome") == "success"])
        human_overrides = len([d for d in decisions if d.get("human_override")])

        return {
            "total_decisions": len(decisions),
            "success_rate": successful_decisions / len(decisions),
            "override_rate": human_overrides / len(decisions),
            "average_confidence": sum(d.get("confidence", 0) for d in decisions) / len(decisions),
            "decision_types": self._count_decision_types(decisions),
            "autonomy_levels": self._count_autonomy_levels(decisions)
        }

    async def _generate_autonomy_insights(
        self,
        decisions: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate insights about autonomy performance"""

        insights = []

        success_rate = metrics.get("success_rate", 0)
        if success_rate > 0.9:
            insights.append({
                "type": "positive",
                "message": f"Excellent autonomy performance with {success_rate:.1%} success rate"
            })
        elif success_rate < 0.7:
            insights.append({
                "type": "warning",
                "message": f"Low autonomy success rate: {success_rate:.1%}. Consider lowering autonomy levels."
            })

        override_rate = metrics.get("override_rate", 0)
        if override_rate > 0.3:
            insights.append({
                "type": "warning",
                "message": f"High override rate: {override_rate:.1%}. Review autonomy thresholds."
            })

        return insights

    def _suggest_autonomy_adjustments(
        self,
        metrics: Dict[str, Any],
        insights: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Suggest autonomy level adjustments"""

        adjustments = []

        success_rate = metrics.get("success_rate", 0)
        override_rate = metrics.get("override_rate", 0)

        if success_rate > 0.9 and override_rate < 0.1:
            adjustments.append({
                "type": "increase_autonomy",
                "recommendation": "Consider increasing autonomy levels",
                "confidence": 0.8
            })

        if success_rate < 0.7 or override_rate > 0.3:
            adjustments.append({
                "type": "decrease_autonomy",
                "recommendation": "Consider decreasing autonomy levels or increasing confidence thresholds",
                "confidence": 0.9
            })

        return adjustments

    def _count_decision_types(self, decisions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count decisions by type"""

        types = {}
        for decision in decisions:
            decision_type = decision.get("decision_type", "unknown")
            types[decision_type] = types.get(decision_type, 0) + 1

        return types

    def _count_autonomy_levels(self, decisions: List[Dict[str, Any]]) -> Dict[int, int]:
        """Count decisions by autonomy level"""

        levels = {}
        for decision in decisions:
            level = decision.get("autonomy_level", 1)
            levels[level] = levels.get(level, 0) + 1

        return levels