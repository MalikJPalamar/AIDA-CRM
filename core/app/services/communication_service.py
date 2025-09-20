"""
AIDA-CRM Communication Service
Email and SMS communication workflows with autonomy levels
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import structlog
import httpx

from ..models.communications import Communication, CommunicationType, CommunicationDirection, CommunicationStatus
from ..models.leads import Lead
from ..services.ai_service import AIService
from ..services.nats_client import get_nats_client
from ..core.config import settings

logger = structlog.get_logger()


class CommunicationService:
    """Service for managing email and SMS communications"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()

    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        lead_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        template_id: Optional[str] = None,
        personalization_data: Optional[Dict[str, Any]] = None,
        autonomy_level: int = 1
    ) -> Dict[str, Any]:
        """Send email with tracking and autonomy controls"""

        try:
            # AI content enhancement if requested
            if autonomy_level >= 3 and personalization_data:
                enhanced_content = await self._enhance_email_content(
                    content, personalization_data
                )
                if enhanced_content != content:
                    logger.info("AI-enhanced email content", email=to_email)
                    content = enhanced_content

            # Create communication record
            communication = Communication(
                lead_id=lead_id,
                deal_id=deal_id,
                type=CommunicationType.EMAIL.value,
                direction=CommunicationDirection.OUTBOUND.value,
                subject=subject,
                content=content,
                status=CommunicationStatus.DRAFT.value if autonomy_level <= 2 else CommunicationStatus.SENT.value,
                sent_by=sender_id,
                metadata={
                    "template_id": template_id,
                    "personalization_data": personalization_data,
                    "autonomy_level": autonomy_level
                }
            )

            # Save to database
            self.db.add(communication)
            await self.db.commit()
            await self.db.refresh(communication)

            # Send email if autonomy level allows
            if autonomy_level >= 3:
                delivery_result = await self._deliver_email(
                    to_email, subject, content, str(communication.id)
                )

                # Update communication status
                communication.status = delivery_result["status"]
                communication.sent_at = datetime.utcnow() if delivery_result["sent"] else None
                await self.db.commit()

                # Publish event
                await self._publish_communication_event("comms.sent", communication)

            result = {
                "communication_id": str(communication.id),
                "status": communication.status,
                "sent": communication.status == CommunicationStatus.SENT.value,
                "requires_approval": autonomy_level <= 2,
                "delivery_info": delivery_result if autonomy_level >= 3 else None
            }

            logger.info(
                "Email communication created",
                communication_id=str(communication.id),
                to_email=to_email,
                status=communication.status,
                autonomy_level=autonomy_level
            )

            return result

        except Exception as e:
            await self.db.rollback()
            logger.error("Email send failed", to_email=to_email, error=str(e))
            raise

    async def send_sms(
        self,
        to_phone: str,
        message: str,
        lead_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        autonomy_level: int = 1
    ) -> Dict[str, Any]:
        """Send SMS with tracking and autonomy controls"""

        try:
            # AI message optimization for SMS character limits
            if autonomy_level >= 3 and len(message) > 160:
                optimized_message = await self._optimize_sms_content(message)
                if optimized_message != message:
                    logger.info("AI-optimized SMS content", phone=to_phone)
                    message = optimized_message

            # Create communication record
            communication = Communication(
                lead_id=lead_id,
                deal_id=deal_id,
                type=CommunicationType.SMS.value,
                direction=CommunicationDirection.OUTBOUND.value,
                content=message,
                status=CommunicationStatus.DRAFT.value if autonomy_level <= 2 else CommunicationStatus.SENT.value,
                sent_by=sender_id,
                metadata={
                    "autonomy_level": autonomy_level,
                    "character_count": len(message)
                }
            )

            # Save to database
            self.db.add(communication)
            await self.db.commit()
            await self.db.refresh(communication)

            # Send SMS if autonomy level allows
            if autonomy_level >= 3:
                delivery_result = await self._deliver_sms(
                    to_phone, message, str(communication.id)
                )

                # Update communication status
                communication.status = delivery_result["status"]
                communication.sent_at = datetime.utcnow() if delivery_result["sent"] else None
                await self.db.commit()

                # Publish event
                await self._publish_communication_event("comms.sent", communication)

            result = {
                "communication_id": str(communication.id),
                "status": communication.status,
                "sent": communication.status == CommunicationStatus.SENT.value,
                "requires_approval": autonomy_level <= 2,
                "delivery_info": delivery_result if autonomy_level >= 3 else None
            }

            logger.info(
                "SMS communication created",
                communication_id=str(communication.id),
                to_phone=to_phone,
                status=communication.status,
                autonomy_level=autonomy_level
            )

            return result

        except Exception as e:
            await self.db.rollback()
            logger.error("SMS send failed", to_phone=to_phone, error=str(e))
            raise

    async def create_email_sequence(
        self,
        lead_id: str,
        sequence_type: str = "welcome",
        autonomy_level: int = 1,
        delay_hours: List[int] = [0, 24, 72, 168]  # immediate, 1 day, 3 days, 1 week
    ) -> Dict[str, Any]:
        """Create automated email sequence for lead nurturing"""

        try:
            # Get lead information
            query = select(Lead).where(Lead.id == lead_id)
            result = await self.db.execute(query)
            lead = result.scalar_one_or_none()

            if not lead:
                raise ValueError(f"Lead {lead_id} not found")

            # Generate sequence content
            sequence_emails = await self._generate_email_sequence(lead, sequence_type)

            # Create scheduled communications
            sequence_id = f"seq_{sequence_type}_{lead_id}_{int(datetime.utcnow().timestamp())}"
            communications = []

            for i, (delay, email_data) in enumerate(zip(delay_hours, sequence_emails)):
                scheduled_time = datetime.utcnow() + timedelta(hours=delay)

                communication = Communication(
                    lead_id=lead_id,
                    type=CommunicationType.EMAIL.value,
                    direction=CommunicationDirection.OUTBOUND.value,
                    subject=email_data["subject"],
                    content=email_data["content"],
                    status=CommunicationStatus.DRAFT.value,
                    metadata={
                        "sequence_id": sequence_id,
                        "sequence_step": i + 1,
                        "scheduled_time": scheduled_time.isoformat(),
                        "autonomy_level": autonomy_level,
                        "sequence_type": sequence_type
                    }
                )

                self.db.add(communication)
                communications.append(communication)

            await self.db.commit()

            # If high autonomy, schedule immediate execution
            if autonomy_level >= 4:
                await self._schedule_sequence_execution(sequence_id, communications)

            result = {
                "sequence_id": sequence_id,
                "emails_created": len(communications),
                "sequence_type": sequence_type,
                "lead_email": lead.email,
                "scheduled": autonomy_level >= 4,
                "requires_approval": autonomy_level <= 3
            }

            logger.info(
                "Email sequence created",
                sequence_id=sequence_id,
                lead_id=lead_id,
                emails_count=len(communications),
                autonomy_level=autonomy_level
            )

            return result

        except Exception as e:
            await self.db.rollback()
            logger.error("Email sequence creation failed", lead_id=lead_id, error=str(e))
            raise

    async def track_email_engagement(
        self,
        communication_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track email engagement events (opens, clicks, replies)"""

        try:
            # Get communication record
            query = select(Communication).where(Communication.id == communication_id)
            result = await self.db.execute(query)
            communication = result.scalar_one_or_none()

            if not communication:
                logger.warning("Communication not found for tracking", communication_id=communication_id)
                return False

            # Update engagement timestamps
            now = datetime.utcnow()

            if event_type == "opened" and not communication.opened_at:
                communication.opened_at = now
                communication.status = CommunicationStatus.OPENED.value

            elif event_type == "clicked" and not communication.clicked_at:
                communication.clicked_at = now
                communication.status = CommunicationStatus.CLICKED.value

            elif event_type == "replied" and not communication.replied_at:
                communication.replied_at = now
                communication.status = CommunicationStatus.REPLIED.value

            # Update metadata with event details
            metadata = communication.metadata or {}
            if "engagement_events" not in metadata:
                metadata["engagement_events"] = []

            metadata["engagement_events"].append({
                "type": event_type,
                "timestamp": now.isoformat(),
                "data": event_data
            })

            communication.metadata = metadata
            await self.db.commit()

            # Publish engagement event
            await self._publish_communication_event(f"comms.{event_type}", communication)

            logger.info(
                "Email engagement tracked",
                communication_id=communication_id,
                event_type=event_type,
                lead_id=str(communication.lead_id) if communication.lead_id else None
            )

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error("Email engagement tracking failed", communication_id=communication_id, error=str(e))
            return False

    async def get_communication_history(
        self,
        lead_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get communication history for a lead or deal"""

        try:
            query = select(Communication)

            if lead_id:
                query = query.where(Communication.lead_id == lead_id)
            elif deal_id:
                query = query.where(Communication.deal_id == deal_id)
            else:
                raise ValueError("Either lead_id or deal_id must be provided")

            query = query.order_by(Communication.created_at.desc()).limit(limit)

            result = await self.db.execute(query)
            communications = result.scalars().all()

            return [self._communication_to_dict(comm) for comm in communications]

        except Exception as e:
            logger.error("Failed to get communication history", error=str(e))
            raise

    async def _enhance_email_content(
        self,
        content: str,
        personalization_data: Dict[str, Any]
    ) -> str:
        """Use AI to enhance email content with personalization"""

        try:
            enhanced = await self.ai_service.generate_email_content(
                lead_data=personalization_data,
                email_type="personalized",
                personalization_data={"original_content": content}
            )
            return enhanced.get("content", content)

        except Exception as e:
            logger.warning("AI email enhancement failed", error=str(e))
            return content

    async def _optimize_sms_content(self, message: str) -> str:
        """Optimize SMS content for character limits"""

        try:
            # Simple optimization - in production, use AI for better results
            if len(message) <= 160:
                return message

            # Basic truncation with AI enhancement
            prompt = f"Shorten this message to under 160 characters while keeping the key information: {message}"

            # Use AI service for optimization
            response = await self.ai_service._make_llm_request(
                prompt=prompt,
                system_message="You are an expert at writing concise SMS messages. Return only the shortened message."
            )

            optimized = response.strip()
            return optimized if len(optimized) <= 160 else message[:157] + "..."

        except Exception as e:
            logger.warning("SMS optimization failed", error=str(e))
            return message[:157] + "..." if len(message) > 160 else message

    async def _generate_email_sequence(
        self,
        lead: Lead,
        sequence_type: str
    ) -> List[Dict[str, str]]:
        """Generate email sequence content based on lead data"""

        lead_data = {
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company": lead.company,
            "source": lead.source,
            "email": lead.email
        }

        sequences = {
            "welcome": [
                {"type": "welcome", "title": "Welcome"},
                {"type": "value_proposition", "title": "Our Value"},
                {"type": "social_proof", "title": "Customer Success"},
                {"type": "call_to_action", "title": "Next Steps"}
            ],
            "nurture": [
                {"type": "educational", "title": "Industry Insights"},
                {"type": "case_study", "title": "Success Story"},
                {"type": "demo_offer", "title": "See It In Action"},
                {"type": "consultation", "title": "Free Consultation"}
            ],
            "re_engagement": [
                {"type": "check_in", "title": "Checking In"},
                {"type": "new_features", "title": "What's New"},
                {"type": "special_offer", "title": "Exclusive Offer"},
                {"type": "final_touch", "title": "Final Follow-up"}
            ]
        }

        sequence_emails = []
        email_configs = sequences.get(sequence_type, sequences["welcome"])

        for config in email_configs:
            try:
                email_content = await self.ai_service.generate_email_content(
                    lead_data=lead_data,
                    email_type=config["type"],
                    personalization_data={"sequence_step": config["title"]}
                )

                sequence_emails.append({
                    "subject": email_content.get("subject", f"{config['title']} - AIDA-CRM"),
                    "content": email_content.get("content", f"Thank you for your interest, {lead.first_name or 'there'}!")
                })

            except Exception as e:
                logger.warning("Email generation failed for sequence step", error=str(e), step=config["type"])
                # Fallback content
                sequence_emails.append({
                    "subject": f"{config['title']} - AIDA-CRM",
                    "content": f"Hi {lead.first_name or 'there'},\n\nThank you for your interest in AIDA-CRM.\n\nBest regards,\nThe AIDA-CRM Team"
                })

        return sequence_emails

    async def _deliver_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        communication_id: str
    ) -> Dict[str, Any]:
        """Deliver email via external service (mock implementation)"""

        try:
            # In production, integrate with email service (SendGrid, SES, etc.)
            # For now, simulate email delivery

            # Mock delivery delay
            import asyncio
            await asyncio.sleep(0.1)

            # Simulate success/failure
            import random
            success = random.random() > 0.05  # 95% success rate

            result = {
                "sent": success,
                "status": CommunicationStatus.SENT.value if success else CommunicationStatus.FAILED.value,
                "provider": "mock_email_service",
                "provider_id": f"mock_{communication_id}",
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info("Email delivery attempted", to_email=to_email, success=success)
            return result

        except Exception as e:
            logger.error("Email delivery failed", to_email=to_email, error=str(e))
            return {
                "sent": False,
                "status": CommunicationStatus.FAILED.value,
                "error": str(e)
            }

    async def _deliver_sms(
        self,
        to_phone: str,
        message: str,
        communication_id: str
    ) -> Dict[str, Any]:
        """Deliver SMS via external service (mock implementation)"""

        try:
            # In production, integrate with SMS service (Twilio, AWS SNS, etc.)
            # For now, simulate SMS delivery

            # Mock delivery delay
            import asyncio
            await asyncio.sleep(0.1)

            # Simulate success/failure
            import random
            success = random.random() > 0.02  # 98% success rate

            result = {
                "sent": success,
                "status": CommunicationStatus.SENT.value if success else CommunicationStatus.FAILED.value,
                "provider": "mock_sms_service",
                "provider_id": f"sms_mock_{communication_id}",
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info("SMS delivery attempted", to_phone=to_phone, success=success)
            return result

        except Exception as e:
            logger.error("SMS delivery failed", to_phone=to_phone, error=str(e))
            return {
                "sent": False,
                "status": CommunicationStatus.FAILED.value,
                "error": str(e)
            }

    async def _schedule_sequence_execution(
        self,
        sequence_id: str,
        communications: List[Communication]
    ):
        """Schedule email sequence for automatic execution"""

        for communication in communications:
            metadata = communication.metadata or {}
            scheduled_time = metadata.get("scheduled_time")

            if scheduled_time:
                # In production, use a job queue (Celery, RQ, etc.)
                # For now, just log the scheduling
                logger.info(
                    "Email scheduled for execution",
                    communication_id=str(communication.id),
                    scheduled_time=scheduled_time,
                    sequence_id=sequence_id
                )

    async def _publish_communication_event(
        self,
        subject: str,
        communication: Communication
    ):
        """Publish communication event to NATS"""

        try:
            nats_client = await get_nats_client()
            event_data = {
                "communication_id": str(communication.id),
                "lead_id": str(communication.lead_id) if communication.lead_id else None,
                "deal_id": str(communication.deal_id) if communication.deal_id else None,
                "type": communication.type,
                "status": communication.status,
                "direction": communication.direction
            }

            await nats_client.publish_event(subject, event_data)

        except Exception as e:
            logger.warning("Failed to publish communication event", error=str(e))

    def _communication_to_dict(self, communication: Communication) -> Dict[str, Any]:
        """Convert communication model to dictionary"""

        return {
            "id": str(communication.id),
            "lead_id": str(communication.lead_id) if communication.lead_id else None,
            "deal_id": str(communication.deal_id) if communication.deal_id else None,
            "type": communication.type,
            "direction": communication.direction,
            "subject": communication.subject,
            "content": communication.content,
            "status": communication.status,
            "sent_by": str(communication.sent_by) if communication.sent_by else None,
            "sent_at": communication.sent_at.isoformat() if communication.sent_at else None,
            "opened_at": communication.opened_at.isoformat() if communication.opened_at else None,
            "clicked_at": communication.clicked_at.isoformat() if communication.clicked_at else None,
            "replied_at": communication.replied_at.isoformat() if communication.replied_at else None,
            "metadata": communication.metadata,
            "created_at": communication.created_at.isoformat() if communication.created_at else None
        }