"""
AIDA-CRM Lead Qualification Engine
Advanced AI-powered lead scoring with L1-L5 autonomy levels
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog

from ..models.leads import Lead, LeadStatus
from ..models.users import User
from ..services.ai_service import AIService
from ..services.source_attribution import SourceAttributionService
from ..core.config import settings

logger = structlog.get_logger()


class QualificationEngine:
    """Advanced lead qualification with AI and autonomy levels"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.attribution_service = SourceAttributionService(db)

    async def qualify_lead(
        self,
        lead_data: Dict[str, Any],
        autonomy_level: int = 1,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Comprehensive lead qualification with multiple scoring models"""

        try:
            # Multi-dimensional scoring
            scores = await self._calculate_all_scores(lead_data)

            # Composite qualification score
            composite_score = self._calculate_composite_score(scores)

            # Confidence assessment
            confidence = self._calculate_confidence(scores, lead_data)

            # Qualification decision based on autonomy level
            qualification_result = await self._make_qualification_decision(
                composite_score,
                confidence,
                autonomy_level,
                scores
            )

            # Generate insights and recommendations
            insights = await self._generate_insights(lead_data, scores, qualification_result)

            # Determine next actions based on autonomy level
            next_actions = await self._determine_next_actions(
                qualification_result,
                autonomy_level,
                lead_data,
                user_id
            )

            logger.info(
                "Lead qualification completed",
                email=lead_data.get("email"),
                composite_score=composite_score,
                confidence=confidence,
                qualification=qualification_result["status"],
                autonomy_level=autonomy_level
            )

            return {
                "qualification_score": composite_score,
                "confidence": confidence,
                "status": qualification_result["status"],
                "reason": qualification_result["reason"],
                "scores_breakdown": scores,
                "insights": insights,
                "next_actions": next_actions,
                "autonomy_level": autonomy_level,
                "requires_human_review": qualification_result["requires_human_review"]
            }

        except Exception as e:
            logger.error("Lead qualification failed", error=str(e))
            # Return safe defaults
            return {
                "qualification_score": 0.5,
                "confidence": 0.3,
                "status": "pending",
                "reason": "Qualification engine error",
                "scores_breakdown": {},
                "insights": [],
                "next_actions": ["manual_review"],
                "autonomy_level": 1,
                "requires_human_review": True
            }

    async def _calculate_all_scores(self, lead_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate multiple scoring dimensions"""

        scores = {}

        # 1. AI-powered semantic score
        scores["ai_semantic"] = await self._calculate_ai_score(lead_data)

        # 2. Data completeness score
        scores["data_completeness"] = self._calculate_completeness_score(lead_data)

        # 3. Source quality score
        scores["source_quality"] = await self._calculate_source_score(lead_data)

        # 4. Demographic fit score
        scores["demographic_fit"] = self._calculate_demographic_score(lead_data)

        # 5. Behavioral intent score
        scores["behavioral_intent"] = self._calculate_intent_score(lead_data)

        # 6. Firmographic score (for B2B)
        scores["firmographic"] = await self._calculate_firmographic_score(lead_data)

        # 7. Timing/urgency score
        scores["urgency"] = self._calculate_urgency_score(lead_data)

        return scores

    async def _calculate_ai_score(self, lead_data: Dict[str, Any]) -> float:
        """AI-powered qualification using LLM"""
        try:
            # Enhanced prompt for better scoring
            ai_score = await self.ai_service.qualify_lead(lead_data)
            return min(max(ai_score, 0.0), 1.0)
        except Exception as e:
            logger.warning("AI scoring failed", error=str(e))
            return 0.5

    def _calculate_completeness_score(self, lead_data: Dict[str, Any]) -> float:
        """Score based on data completeness"""

        required_fields = ["email"]
        important_fields = ["first_name", "last_name", "company"]
        optional_fields = ["phone", "campaign", "utm_params"]

        score = 0.0

        # Required fields (must have)
        for field in required_fields:
            if lead_data.get(field):
                score += 0.3

        # Important fields
        for field in important_fields:
            if lead_data.get(field):
                score += 0.15

        # Optional fields
        for field in optional_fields:
            if lead_data.get(field):
                score += 0.05

        # UTM parameter completeness
        utm_params = lead_data.get("utm_params", {})
        if isinstance(utm_params, dict) and len(utm_params) >= 3:
            score += 0.1

        return min(score, 1.0)

    async def _calculate_source_score(self, lead_data: Dict[str, Any]) -> float:
        """Score based on lead source quality"""

        source_analysis = await self.attribution_service.analyze_lead_source(lead_data)
        return source_analysis.get("quality_score", 0.5)

    def _calculate_demographic_score(self, lead_data: Dict[str, Any]) -> float:
        """Score based on demographic indicators"""

        score = 0.5  # Base score

        # Email domain analysis
        email = lead_data.get("email", "")
        if email:
            domain = email.split("@")[-1].lower()

            # Business email indicators
            if any(domain.endswith(tld) for tld in [".com", ".org", ".net"]):
                score += 0.1

            # Free email providers (lower score)
            free_providers = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
            if domain in free_providers:
                score -= 0.1

            # Corporate domains (higher score)
            if domain not in free_providers and "." in domain:
                score += 0.2

        # Name completeness
        if lead_data.get("first_name") and lead_data.get("last_name"):
            score += 0.1

        # Company presence
        company = lead_data.get("company", "")
        if company and len(company) > 2:
            score += 0.2

        return min(max(score, 0.0), 1.0)

    def _calculate_intent_score(self, lead_data: Dict[str, Any]) -> float:
        """Score based on behavioral intent signals"""

        score = 0.5  # Base score

        # UTM analysis for intent
        utm_params = lead_data.get("utm_params", {})
        if isinstance(utm_params, dict):
            campaign = utm_params.get("utm_campaign", "").lower()
            term = utm_params.get("utm_term", "").lower()
            content = utm_params.get("utm_content", "").lower()

            # High intent keywords
            high_intent = ["buy", "purchase", "demo", "trial", "pricing", "quote"]
            if any(keyword in f"{campaign} {term} {content}" for keyword in high_intent):
                score += 0.3

            # Medium intent keywords
            medium_intent = ["learn", "guide", "how", "solution", "product"]
            if any(keyword in f"{campaign} {term} {content}" for keyword in medium_intent):
                score += 0.1

        # Source-based intent
        source = lead_data.get("source", "").lower()
        if source in ["demo_request", "pricing_page", "contact_sales"]:
            score += 0.3
        elif source in ["newsletter", "blog", "content_download"]:
            score += 0.1

        # Custom fields analysis
        custom_fields = lead_data.get("custom_fields", {})
        if isinstance(custom_fields, dict):
            # Look for budget, timeline, decision authority indicators
            if any(key in str(custom_fields).lower() for key in ["budget", "timeline", "decision"]):
                score += 0.2

        return min(max(score, 0.0), 1.0)

    async def _calculate_firmographic_score(self, lead_data: Dict[str, Any]) -> float:
        """Score based on company/firmographic data"""

        score = 0.5  # Base score

        company = lead_data.get("company", "")
        if not company:
            return 0.3

        # Company name analysis
        if len(company) >= 3:
            score += 0.1

        # Industry indicators (would be enhanced with external data)
        # For now, basic heuristics
        tech_indicators = ["tech", "software", "digital", "data", "analytics", "ai"]
        if any(indicator in company.lower() for indicator in tech_indicators):
            score += 0.2

        # Size indicators
        size_indicators = ["inc", "corp", "ltd", "llc", "group", "international"]
        if any(indicator in company.lower() for indicator in size_indicators):
            score += 0.1

        return min(max(score, 0.0), 1.0)

    def _calculate_urgency_score(self, lead_data: Dict[str, Any]) -> float:
        """Score based on timing and urgency signals"""

        score = 0.5  # Base score

        # Time-based urgency
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Business hours
            score += 0.1

        # Source urgency
        urgent_sources = ["phone", "chat", "demo_request", "contact_sales"]
        if lead_data.get("source") in urgent_sources:
            score += 0.3

        # Campaign urgency
        campaign = lead_data.get("campaign", "").lower()
        urgent_keywords = ["urgent", "immediate", "now", "today", "asap"]
        if any(keyword in campaign for keyword in urgent_keywords):
            score += 0.2

        return min(max(score, 0.0), 1.0)

    def _calculate_composite_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted composite score"""

        # Weights for different score dimensions
        weights = {
            "ai_semantic": 0.25,
            "data_completeness": 0.15,
            "source_quality": 0.15,
            "demographic_fit": 0.15,
            "behavioral_intent": 0.15,
            "firmographic": 0.10,
            "urgency": 0.05
        }

        composite = 0.0
        total_weight = 0.0

        for dimension, score in scores.items():
            weight = weights.get(dimension, 0.1)
            composite += score * weight
            total_weight += weight

        # Normalize if weights don't sum to 1
        if total_weight > 0:
            composite = composite / total_weight

        return min(max(composite, 0.0), 1.0)

    def _calculate_confidence(self, scores: Dict[str, float], lead_data: Dict[str, Any]) -> float:
        """Calculate confidence in the qualification decision"""

        # Base confidence from data completeness
        base_confidence = scores.get("data_completeness", 0.5)

        # Reduce confidence if scores are highly variable
        score_values = list(scores.values())
        if len(score_values) > 1:
            score_std = (sum((x - sum(score_values)/len(score_values))**2 for x in score_values) / len(score_values))**0.5
            variability_penalty = min(score_std, 0.3)
            base_confidence -= variability_penalty

        # Increase confidence for certain sources
        reliable_sources = ["hubspot", "salesforce", "calendly", "demo_request"]
        if lead_data.get("source") in reliable_sources:
            base_confidence += 0.1

        return min(max(base_confidence, 0.1), 1.0)

    async def _make_qualification_decision(
        self,
        composite_score: float,
        confidence: float,
        autonomy_level: int,
        scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Make qualification decision based on autonomy level"""

        # Define thresholds based on autonomy level
        thresholds = {
            1: {"qualified": 0.9, "confidence": 0.9},  # L1: Very conservative
            2: {"qualified": 0.8, "confidence": 0.8},  # L2: Conservative
            3: {"qualified": 0.7, "confidence": 0.7},  # L3: Moderate
            4: {"qualified": 0.6, "confidence": 0.6},  # L4: Aggressive
            5: {"qualified": 0.5, "confidence": 0.5},  # L5: Very aggressive
        }

        level_threshold = thresholds.get(autonomy_level, thresholds[1])

        # Decision logic
        if composite_score >= level_threshold["qualified"] and confidence >= level_threshold["confidence"]:
            status = "qualified"
            reason = f"Meets L{autonomy_level} qualification criteria (score: {composite_score:.2f}, confidence: {confidence:.2f})"
            requires_review = autonomy_level <= 2
        elif composite_score < 0.3:
            status = "unqualified"
            reason = f"Below minimum qualification threshold (score: {composite_score:.2f})"
            requires_review = autonomy_level <= 3
        else:
            status = "pending"
            reason = f"Requires review - borderline qualification (score: {composite_score:.2f}, confidence: {confidence:.2f})"
            requires_review = True

        return {
            "status": status,
            "reason": reason,
            "requires_human_review": requires_review
        }

    async def _generate_insights(
        self,
        lead_data: Dict[str, Any],
        scores: Dict[str, float],
        qualification_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable insights about the lead"""

        insights = []

        # Score-based insights
        for dimension, score in scores.items():
            if score >= 0.8:
                insights.append({
                    "type": "strength",
                    "dimension": dimension,
                    "message": f"Strong {dimension.replace('_', ' ')} signals",
                    "confidence": 0.8
                })
            elif score <= 0.3:
                insights.append({
                    "type": "weakness",
                    "dimension": dimension,
                    "message": f"Weak {dimension.replace('_', ' ')} indicators",
                    "confidence": 0.7
                })

        # Data quality insights
        missing_fields = []
        for field in ["first_name", "last_name", "company", "phone"]:
            if not lead_data.get(field):
                missing_fields.append(field)

        if missing_fields:
            insights.append({
                "type": "data_gap",
                "dimension": "data_completeness",
                "message": f"Missing data: {', '.join(missing_fields)}",
                "confidence": 0.9
            })

        # Qualification insights
        if qualification_result["status"] == "qualified":
            insights.append({
                "type": "recommendation",
                "dimension": "next_steps",
                "message": "High-priority lead - immediate follow-up recommended",
                "confidence": 0.8
            })
        elif qualification_result["status"] == "pending":
            insights.append({
                "type": "recommendation",
                "dimension": "next_steps",
                "message": "Needs additional qualification - consider nurture sequence",
                "confidence": 0.7
            })

        return insights

    async def _determine_next_actions(
        self,
        qualification_result: Dict[str, Any],
        autonomy_level: int,
        lead_data: Dict[str, Any],
        user_id: Optional[str]
    ) -> List[str]:
        """Determine next actions based on qualification and autonomy level"""

        actions = []
        status = qualification_result["status"]

        if status == "qualified":
            if autonomy_level >= 4:
                actions.extend([
                    "auto_assign_to_sales",
                    "send_welcome_email",
                    "schedule_follow_up_task",
                    "add_to_hot_leads_list"
                ])
            elif autonomy_level >= 3:
                actions.extend([
                    "assign_to_sales",
                    "send_welcome_email",
                    "create_follow_up_task"
                ])
            else:
                actions.extend([
                    "notify_sales_team",
                    "draft_welcome_email",
                    "flag_for_immediate_review"
                ])

        elif status == "pending":
            if autonomy_level >= 3:
                actions.extend([
                    "add_to_nurture_sequence",
                    "request_additional_info",
                    "score_monitoring"
                ])
            else:
                actions.extend([
                    "flag_for_manual_review",
                    "queue_for_qualification_call"
                ])

        else:  # unqualified
            if autonomy_level >= 4:
                actions.extend([
                    "add_to_newsletter",
                    "tag_as_future_opportunity"
                ])
            else:
                actions.extend([
                    "review_disqualification",
                    "consider_nurture_campaign"
                ])

        # Add source-specific actions
        source = lead_data.get("source", "")
        if source == "demo_request":
            actions.insert(0, "schedule_demo")
        elif source in ["pricing_page", "contact_sales"]:
            actions.insert(0, "priority_sales_contact")

        return actions

    async def batch_qualify_leads(
        self,
        autonomy_level: int = 1,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Batch process unqualified leads"""

        # Get unqualified leads
        query = select(Lead).where(
            and_(
                Lead.status == LeadStatus.NEW.value,
                Lead.qualification_score.is_(None)
            )
        ).limit(limit)

        result = await self.db.execute(query)
        leads = result.scalars().all()

        results = {
            "processed": 0,
            "qualified": 0,
            "unqualified": 0,
            "pending": 0,
            "errors": 0
        }

        for lead in leads:
            try:
                # Convert lead to data dict
                lead_data = {
                    "email": lead.email,
                    "first_name": lead.first_name,
                    "last_name": lead.last_name,
                    "company": lead.company,
                    "phone": lead.phone,
                    "source": lead.source,
                    "campaign": lead.campaign,
                    "utm_params": lead.utm_params,
                    "custom_fields": lead.custom_fields
                }

                # Qualify the lead
                qualification = await self.qualify_lead(lead_data, autonomy_level)

                # Update lead record
                lead.qualification_score = qualification["qualification_score"]
                lead.status = qualification["status"]

                results["processed"] += 1
                results[qualification["status"]] += 1

                await self.db.commit()

            except Exception as e:
                logger.error("Batch qualification error", lead_id=str(lead.id), error=str(e))
                results["errors"] += 1
                await self.db.rollback()

        return results