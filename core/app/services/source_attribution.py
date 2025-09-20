"""
AIDA-CRM Source Attribution Service
Advanced lead source tracking and campaign attribution
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import structlog

from ..models.leads import Lead
from ..models.communications import Communication

logger = structlog.get_logger()


class SourceAttributionService:
    """Service for tracking and analyzing lead sources and attribution"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_lead_source(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and enrich lead source information"""

        source = lead_data.get("source", "unknown")
        utm_params = lead_data.get("utm_params", {})

        # Enhanced source categorization
        source_info = self._categorize_source(source, utm_params)

        # Calculate source quality score
        quality_score = self._calculate_source_quality(source_info, lead_data)

        # Attribution modeling
        attribution = await self._apply_attribution_model(lead_data)

        return {
            "source_category": source_info["category"],
            "source_subcategory": source_info["subcategory"],
            "quality_score": quality_score,
            "attribution": attribution,
            "enriched_utm": self._enrich_utm_params(utm_params),
            "first_touch": await self._identify_first_touch(lead_data),
            "last_touch": source_info,
        }

    def _categorize_source(self, source: str, utm_params: Dict[str, str]) -> Dict[str, str]:
        """Categorize lead source into primary categories"""

        # Direct source mapping
        source_categories = {
            # Paid channels
            "google_ads": {"category": "paid", "subcategory": "search"},
            "facebook": {"category": "paid", "subcategory": "social"},
            "linkedin": {"category": "paid", "subcategory": "social"},
            "bing_ads": {"category": "paid", "subcategory": "search"},
            "twitter_ads": {"category": "paid", "subcategory": "social"},

            # Organic channels
            "google": {"category": "organic", "subcategory": "search"},
            "bing": {"category": "organic", "subcategory": "search"},
            "yahoo": {"category": "organic", "subcategory": "search"},

            # Social media
            "twitter": {"category": "social", "subcategory": "organic"},
            "instagram": {"category": "social", "subcategory": "organic"},
            "tiktok": {"category": "social", "subcategory": "organic"},

            # Email marketing
            "email": {"category": "email", "subcategory": "campaign"},
            "newsletter": {"category": "email", "subcategory": "newsletter"},

            # Referral
            "referral": {"category": "referral", "subcategory": "partner"},
            "affiliate": {"category": "referral", "subcategory": "affiliate"},

            # Direct
            "direct": {"category": "direct", "subcategory": "direct"},
            "website": {"category": "direct", "subcategory": "website"},

            # Content marketing
            "blog": {"category": "content", "subcategory": "blog"},
            "webinar": {"category": "content", "subcategory": "webinar"},
            "ebook": {"category": "content", "subcategory": "download"},

            # Events
            "event": {"category": "event", "subcategory": "conference"},
            "tradeshow": {"category": "event", "subcategory": "tradeshow"},
            "webinar": {"category": "event", "subcategory": "webinar"},

            # Forms/Tools
            "hubspot": {"category": "form", "subcategory": "cms"},
            "typeform": {"category": "form", "subcategory": "survey"},
            "calendly": {"category": "form", "subcategory": "booking"},
            "webflow": {"category": "form", "subcategory": "website"},
        }

        # Check direct mapping first
        if source in source_categories:
            return source_categories[source]

        # UTM-based categorization
        utm_source = utm_params.get("utm_source", "").lower()
        utm_medium = utm_params.get("utm_medium", "").lower()

        if utm_medium in ["cpc", "ppc", "paid"]:
            return {"category": "paid", "subcategory": "search"}
        elif utm_medium in ["social", "social-media"]:
            paid_social = utm_source in ["facebook", "linkedin", "twitter", "instagram"]
            return {"category": "paid" if paid_social else "social", "subcategory": "social"}
        elif utm_medium == "email":
            return {"category": "email", "subcategory": "campaign"}
        elif utm_medium == "referral":
            return {"category": "referral", "subcategory": "partner"}
        elif utm_medium == "organic":
            return {"category": "organic", "subcategory": "search"}

        # Default categorization
        return {"category": "unknown", "subcategory": source}

    def _calculate_source_quality(self, source_info: Dict[str, str], lead_data: Dict[str, Any]) -> float:
        """Calculate quality score for the lead source"""

        base_scores = {
            "paid": 0.7,
            "organic": 0.8,
            "referral": 0.9,
            "email": 0.6,
            "social": 0.5,
            "direct": 0.8,
            "content": 0.7,
            "event": 0.9,
            "form": 0.6,
            "unknown": 0.3,
        }

        base_score = base_scores.get(source_info["category"], 0.5)

        # Adjust based on data completeness
        completeness_bonus = 0
        if lead_data.get("first_name"):
            completeness_bonus += 0.1
        if lead_data.get("last_name"):
            completeness_bonus += 0.1
        if lead_data.get("company"):
            completeness_bonus += 0.1
        if lead_data.get("phone"):
            completeness_bonus += 0.1

        # Adjust based on UTM completeness
        utm_params = lead_data.get("utm_params", {})
        if utm_params.get("utm_campaign"):
            completeness_bonus += 0.05
        if utm_params.get("utm_term"):
            completeness_bonus += 0.05

        return min(base_score + completeness_bonus, 1.0)

    async def _apply_attribution_model(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply attribution model to determine source credit"""

        # For now, use last-touch attribution
        # In the future, implement multi-touch attribution

        return {
            "model": "last_touch",
            "primary_source": lead_data.get("source"),
            "attribution_weight": 1.0,
            "touchpoints": [
                {
                    "source": lead_data.get("source"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "weight": 1.0
                }
            ]
        }

    def _enrich_utm_params(self, utm_params: Dict[str, str]) -> Dict[str, Any]:
        """Enrich UTM parameters with additional insights"""

        enriched = utm_params.copy()

        # Classify campaign type
        campaign = utm_params.get("utm_campaign", "").lower()
        if any(keyword in campaign for keyword in ["brand", "branded"]):
            enriched["campaign_type"] = "brand"
        elif any(keyword in campaign for keyword in ["competitor", "comp"]):
            enriched["campaign_type"] = "competitor"
        elif any(keyword in campaign for keyword in ["generic", "category"]):
            enriched["campaign_type"] = "generic"
        elif any(keyword in campaign for keyword in ["retarget", "remarketing"]):
            enriched["campaign_type"] = "retargeting"
        else:
            enriched["campaign_type"] = "other"

        # Extract intent signals from terms
        term = utm_params.get("utm_term", "").lower()
        if any(keyword in term for keyword in ["buy", "purchase", "price", "cost"]):
            enriched["intent_signal"] = "high"
        elif any(keyword in term for keyword in ["demo", "trial", "free"]):
            enriched["intent_signal"] = "medium"
        elif any(keyword in term for keyword in ["learn", "how", "what", "guide"]):
            enriched["intent_signal"] = "low"
        else:
            enriched["intent_signal"] = "unknown"

        return enriched

    async def _identify_first_touch(self, lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Identify first touch point for this lead (if returning)"""

        email = lead_data.get("email")
        if not email:
            return None

        # Check for existing leads with same email
        query = select(Lead).where(Lead.email == email).order_by(Lead.created_at.asc()).limit(1)
        result = await self.db.execute(query)
        first_lead = result.scalar_one_or_none()

        if first_lead and first_lead.created_at < datetime.utcnow() - timedelta(minutes=5):
            return {
                "source": first_lead.source,
                "campaign": first_lead.campaign,
                "timestamp": first_lead.created_at.isoformat(),
                "utm_params": first_lead.utm_params
            }

        return None

    async def get_source_performance(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get performance analytics by source"""

        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=30)
        if not date_to:
            date_to = datetime.utcnow()

        # Lead count by source
        lead_query = select(
            Lead.source,
            func.count(Lead.id).label("lead_count"),
            func.avg(Lead.qualification_score).label("avg_score"),
            func.count(func.nullif(Lead.status == "qualified", False)).label("qualified_count")
        ).where(
            and_(Lead.created_at >= date_from, Lead.created_at <= date_to)
        ).group_by(Lead.source)

        result = await self.db.execute(lead_query)
        source_stats = result.all()

        # Calculate conversion rates and costs
        performance = {}
        for stat in source_stats:
            source = stat.source
            lead_count = stat.lead_count
            qualified_count = stat.qualified_count or 0
            avg_score = float(stat.avg_score) if stat.avg_score else 0

            performance[source] = {
                "lead_count": lead_count,
                "qualified_count": qualified_count,
                "qualification_rate": qualified_count / lead_count if lead_count > 0 else 0,
                "average_score": round(avg_score, 3),
                "source_quality": self._get_source_quality_grade(avg_score),
            }

        return {
            "date_range": {"from": date_from.isoformat(), "to": date_to.isoformat()},
            "performance_by_source": performance,
            "top_sources": sorted(
                performance.items(),
                key=lambda x: x[1]["qualified_count"],
                reverse=True
            )[:10]
        }

    def _get_source_quality_grade(self, avg_score: float) -> str:
        """Convert average score to quality grade"""
        if avg_score >= 0.8:
            return "A"
        elif avg_score >= 0.7:
            return "B"
        elif avg_score >= 0.6:
            return "C"
        elif avg_score >= 0.5:
            return "D"
        else:
            return "F"

    async def get_campaign_attribution(self, campaign: str) -> Dict[str, Any]:
        """Get detailed attribution for a specific campaign"""

        query = select(Lead).where(Lead.campaign == campaign)
        result = await self.db.execute(query)
        leads = result.scalars().all()

        if not leads:
            return {"campaign": campaign, "leads": [], "summary": {}}

        # Analyze campaign performance
        total_leads = len(leads)
        qualified_leads = len([l for l in leads if l.status == "qualified"])
        avg_score = sum(float(l.qualification_score or 0) for l in leads) / total_leads

        # Source breakdown
        source_breakdown = {}
        for lead in leads:
            source = lead.source
            if source not in source_breakdown:
                source_breakdown[source] = {"count": 0, "qualified": 0}
            source_breakdown[source]["count"] += 1
            if lead.status == "qualified":
                source_breakdown[source]["qualified"] += 1

        return {
            "campaign": campaign,
            "summary": {
                "total_leads": total_leads,
                "qualified_leads": qualified_leads,
                "qualification_rate": qualified_leads / total_leads if total_leads > 0 else 0,
                "average_score": round(avg_score, 3),
            },
            "source_breakdown": source_breakdown,
            "leads": [
                {
                    "id": str(lead.id),
                    "email": lead.email,
                    "source": lead.source,
                    "score": float(lead.qualification_score or 0),
                    "status": lead.status,
                    "created_at": lead.created_at.isoformat()
                }
                for lead in leads
            ]
        }