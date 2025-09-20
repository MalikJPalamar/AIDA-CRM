"""
AIDA-CRM Lead Service
Business logic for lead management and qualification
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog

from ..models.leads import Lead, LeadStatus
from ..models.users import User
from ..services.nats_client import get_nats_client
from ..services.ai_service import AIService

logger = structlog.get_logger()


class LeadService:
    """Service for lead management operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()

    async def capture_lead(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        source: str = "web",
        campaign: Optional[str] = None,
        utm_params: Optional[Dict[str, str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Capture a new lead"""

        try:
            # Check for duplicate leads
            existing_lead = await self._get_lead_by_email(email)
            if existing_lead:
                logger.info("Duplicate lead detected", email=email, existing_id=str(existing_lead.id))
                return {
                    "lead_id": str(existing_lead.id),
                    "qualification_score": existing_lead.qualification_score,
                    "message": "Lead already exists",
                    "duplicate": True
                }

            # Create new lead
            lead = Lead(
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company,
                phone=phone,
                source=source,
                campaign=campaign,
                utm_params=utm_params,
                custom_fields=custom_fields,
                assigned_to=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                status=LeadStatus.NEW.value
            )

            # AI qualification
            qualification_score = await self._qualify_lead(lead)
            lead.qualification_score = qualification_score

            # Auto-qualify if score is high enough
            if qualification_score >= 0.7:
                lead.status = LeadStatus.QUALIFIED.value

            # Save to database
            self.db.add(lead)
            await self.db.commit()
            await self.db.refresh(lead)

            # Publish event to NATS
            await self._publish_lead_captured_event(lead)

            # Generate next actions
            next_actions = await self._generate_next_actions(lead)

            logger.info(
                "Lead captured successfully",
                lead_id=str(lead.id),
                email=email,
                score=qualification_score,
                status=lead.status
            )

            return {
                "lead_id": str(lead.id),
                "qualification_score": qualification_score,
                "status": lead.status,
                "next_actions": next_actions,
                "duplicate": False
            }

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to capture lead", email=email, error=str(e))
            raise

    async def get_leads(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get leads with filtering and pagination"""

        try:
            query = select(Lead)

            # Apply filters
            filters = []
            if user_id:
                filters.append(Lead.assigned_to == user_id)
            if status:
                filters.append(Lead.status == status)
            if source:
                filters.append(Lead.source == source)

            if filters:
                query = query.where(and_(*filters))

            # Apply pagination
            query = query.offset(offset).limit(limit).order_by(Lead.created_at.desc())

            result = await self.db.execute(query)
            leads = result.scalars().all()

            return [self._lead_to_dict(lead) for lead in leads]

        except Exception as e:
            logger.error("Failed to get leads", error=str(e))
            raise

    async def get_lead_by_id(self, lead_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a specific lead by ID"""

        try:
            query = select(Lead).where(Lead.id == lead_id)
            result = await self.db.execute(query)
            lead = result.scalar_one_or_none()

            if lead:
                return self._lead_to_dict(lead)
            return None

        except Exception as e:
            logger.error("Failed to get lead", lead_id=str(lead_id), error=str(e))
            raise

    async def update_lead_status(
        self,
        lead_id: UUID,
        status: str,
        user_id: Optional[UUID] = None
    ) -> bool:
        """Update lead status"""

        try:
            query = select(Lead).where(Lead.id == lead_id)
            result = await self.db.execute(query)
            lead = result.scalar_one_or_none()

            if not lead:
                return False

            old_status = lead.status
            lead.status = status

            if user_id:
                lead.assigned_to = user_id

            await self.db.commit()

            # Publish status change event
            await self._publish_lead_status_changed_event(lead, old_status)

            logger.info(
                "Lead status updated",
                lead_id=str(lead_id),
                old_status=old_status,
                new_status=status
            )

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update lead status", lead_id=str(lead_id), error=str(e))
            raise

    async def _get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email address"""
        query = select(Lead).where(Lead.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _qualify_lead(self, lead: Lead) -> float:
        """AI-powered lead qualification"""
        try:
            # Prepare lead data for AI analysis
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

            # Get AI qualification score
            score = await self.ai_service.qualify_lead(lead_data)
            return min(max(score, 0.0), 1.0)  # Ensure score is between 0 and 1

        except Exception as e:
            logger.warning("AI qualification failed, using default score", error=str(e))
            return 0.5  # Default medium score

    async def _generate_next_actions(self, lead: Lead) -> List[str]:
        """Generate suggested next actions for lead"""
        actions = []

        if lead.qualification_score >= 0.8:
            actions.extend(["assign_to_sales", "schedule_demo", "send_premium_content"])
        elif lead.qualification_score >= 0.6:
            actions.extend(["send_welcome_email", "add_to_nurture_sequence"])
        elif lead.qualification_score >= 0.4:
            actions.extend(["send_welcome_email", "request_more_info"])
        else:
            actions.extend(["add_to_general_newsletter"])

        # Add source-specific actions
        if lead.source == "demo_request":
            actions.append("schedule_demo")
        elif lead.source == "content_download":
            actions.append("send_related_content")

        return actions

    async def _publish_lead_captured_event(self, lead: Lead):
        """Publish lead captured event to NATS"""
        try:
            nats_client = await get_nats_client()
            event_data = {
                "lead_id": str(lead.id),
                "email": lead.email,
                "qualification_score": float(lead.qualification_score) if lead.qualification_score else None,
                "status": lead.status,
                "source": lead.source,
                "campaign": lead.campaign
            }

            await nats_client.publish_event("leads.captured", event_data)

        except Exception as e:
            logger.warning("Failed to publish lead captured event", error=str(e))

    async def _publish_lead_status_changed_event(self, lead: Lead, old_status: str):
        """Publish lead status changed event to NATS"""
        try:
            nats_client = await get_nats_client()
            event_data = {
                "lead_id": str(lead.id),
                "email": lead.email,
                "old_status": old_status,
                "new_status": lead.status,
                "qualification_score": float(lead.qualification_score) if lead.qualification_score else None
            }

            subject = f"leads.{lead.status}"  # leads.qualified, leads.rejected, etc.
            await nats_client.publish_event(subject, event_data)

        except Exception as e:
            logger.warning("Failed to publish lead status changed event", error=str(e))

    def _lead_to_dict(self, lead: Lead) -> Dict[str, Any]:
        """Convert lead model to dictionary"""
        return {
            "id": str(lead.id),
            "email": lead.email,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "full_name": lead.full_name,
            "company": lead.company,
            "phone": lead.phone,
            "source": lead.source,
            "campaign": lead.campaign,
            "utm_params": lead.utm_params,
            "custom_fields": lead.custom_fields,
            "qualification_score": float(lead.qualification_score) if lead.qualification_score else None,
            "status": lead.status,
            "is_qualified": lead.is_qualified,
            "assigned_to": str(lead.assigned_to) if lead.assigned_to else None,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "updated_at": lead.updated_at.isoformat() if lead.updated_at else None
        }