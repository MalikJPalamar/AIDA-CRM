"""
AIDA-CRM Webhook Service
Handle incoming webhooks from various lead sources
"""

import hashlib
import hmac
import json
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
import structlog

from ..services.lead_service import LeadService
from ..core.config import settings

logger = structlog.get_logger()


class WebhookService:
    """Service for processing webhooks from external platforms"""

    def __init__(self, lead_service: LeadService):
        self.lead_service = lead_service

    async def process_webhook(
        self,
        source: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """Process incoming webhook based on source"""

        try:
            # Verify webhook signature if provided
            if signature and not self._verify_signature(source, payload, signature):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

            # Route to appropriate handler
            handler_map = {
                "hubspot": self._process_hubspot_webhook,
                "salesforce": self._process_salesforce_webhook,
                "zapier": self._process_zapier_webhook,
                "typeform": self._process_typeform_webhook,
                "facebook": self._process_facebook_webhook,
                "linkedin": self._process_linkedin_webhook,
                "google_ads": self._process_google_ads_webhook,
                "webflow": self._process_webflow_webhook,
                "calendly": self._process_calendly_webhook,
                "custom": self._process_custom_webhook,
            }

            handler = handler_map.get(source)
            if not handler:
                raise HTTPException(status_code=400, detail=f"Unsupported webhook source: {source}")

            # Extract lead data
            lead_data = await handler(payload)

            # Enrich with request metadata
            if request:
                lead_data.update({
                    "ip_address": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "referer": request.headers.get("referer"),
                })

            # Capture the lead
            result = await self.lead_service.capture_lead(**lead_data)

            logger.info(
                "Webhook processed successfully",
                source=source,
                lead_id=result.get("lead_id"),
                email=lead_data.get("email")
            )

            return result

        except Exception as e:
            logger.error("Webhook processing failed", source=source, error=str(e))
            raise

    async def _process_hubspot_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process HubSpot contact form submission"""
        try:
            # HubSpot sends form submissions in this format
            form_data = payload.get("formData", {})
            contact = payload.get("contact", {})

            return {
                "email": form_data.get("email") or contact.get("email"),
                "first_name": form_data.get("firstname") or contact.get("firstname"),
                "last_name": form_data.get("lastname") or contact.get("lastname"),
                "company": form_data.get("company") or contact.get("company"),
                "phone": form_data.get("phone") or contact.get("phone"),
                "source": "hubspot",
                "campaign": payload.get("formGuid"),
                "custom_fields": {
                    "hubspot_contact_id": contact.get("vid"),
                    "form_guid": payload.get("formGuid"),
                    "page_url": payload.get("pageUrl"),
                }
            }
        except Exception as e:
            logger.error("Failed to process HubSpot webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid HubSpot webhook format")

    async def _process_salesforce_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Salesforce lead webhook"""
        try:
            lead = payload.get("sobject", {})

            return {
                "email": lead.get("Email"),
                "first_name": lead.get("FirstName"),
                "last_name": lead.get("LastName"),
                "company": lead.get("Company"),
                "phone": lead.get("Phone"),
                "source": "salesforce",
                "custom_fields": {
                    "salesforce_id": lead.get("Id"),
                    "lead_source": lead.get("LeadSource"),
                    "rating": lead.get("Rating"),
                    "industry": lead.get("Industry"),
                }
            }
        except Exception as e:
            logger.error("Failed to process Salesforce webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid Salesforce webhook format")

    async def _process_zapier_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Zapier webhook (flexible format)"""
        try:
            return {
                "email": payload.get("email"),
                "first_name": payload.get("first_name") or payload.get("name", "").split()[0] if payload.get("name") else None,
                "last_name": payload.get("last_name") or " ".join(payload.get("name", "").split()[1:]) if payload.get("name") and len(payload.get("name", "").split()) > 1 else None,
                "company": payload.get("company"),
                "phone": payload.get("phone"),
                "source": "zapier",
                "campaign": payload.get("campaign") or payload.get("source"),
                "utm_params": {
                    "utm_source": payload.get("utm_source"),
                    "utm_medium": payload.get("utm_medium"),
                    "utm_campaign": payload.get("utm_campaign"),
                    "utm_term": payload.get("utm_term"),
                    "utm_content": payload.get("utm_content"),
                },
                "custom_fields": {k: v for k, v in payload.items() if k not in [
                    "email", "first_name", "last_name", "company", "phone", "campaign", "source"
                ]}
            }
        except Exception as e:
            logger.error("Failed to process Zapier webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid Zapier webhook format")

    async def _process_typeform_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Typeform submission webhook"""
        try:
            form_response = payload.get("form_response", {})
            answers = form_response.get("answers", [])

            # Extract answers by field type
            field_map = {}
            for answer in answers:
                field = answer.get("field", {})
                field_type = field.get("type")
                field_ref = field.get("ref")

                if field_type == "email":
                    field_map["email"] = answer.get("email")
                elif field_type == "short_text" and "name" in field.get("title", "").lower():
                    field_map["name"] = answer.get("text")
                elif field_type == "short_text" and "company" in field.get("title", "").lower():
                    field_map["company"] = answer.get("text")
                elif field_type == "phone_number":
                    field_map["phone"] = answer.get("phone_number")

            # Parse name if provided as single field
            name_parts = field_map.get("name", "").split() if field_map.get("name") else []

            return {
                "email": field_map.get("email"),
                "first_name": name_parts[0] if name_parts else None,
                "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else None,
                "company": field_map.get("company"),
                "phone": field_map.get("phone"),
                "source": "typeform",
                "campaign": form_response.get("form_id"),
                "custom_fields": {
                    "typeform_response_id": form_response.get("token"),
                    "form_id": form_response.get("form_id"),
                    "submitted_at": form_response.get("submitted_at"),
                }
            }
        except Exception as e:
            logger.error("Failed to process Typeform webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid Typeform webhook format")

    async def _process_facebook_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Facebook Lead Ads webhook"""
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            leadgen_data = changes.get("value", {})

            return {
                "email": leadgen_data.get("email"),
                "first_name": leadgen_data.get("first_name"),
                "last_name": leadgen_data.get("last_name"),
                "phone": leadgen_data.get("phone_number"),
                "source": "facebook",
                "campaign": leadgen_data.get("ad_id"),
                "custom_fields": {
                    "facebook_lead_id": leadgen_data.get("leadgen_id"),
                    "ad_id": leadgen_data.get("ad_id"),
                    "form_id": leadgen_data.get("form_id"),
                    "page_id": entry.get("id"),
                }
            }
        except Exception as e:
            logger.error("Failed to process Facebook webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid Facebook webhook format")

    async def _process_linkedin_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process LinkedIn Lead Gen Forms webhook"""
        try:
            lead = payload.get("leadGenFormResponse", {})

            return {
                "email": lead.get("emailAddress"),
                "first_name": lead.get("firstName"),
                "last_name": lead.get("lastName"),
                "company": lead.get("companyName"),
                "phone": lead.get("phoneNumber"),
                "source": "linkedin",
                "campaign": lead.get("campaignId"),
                "custom_fields": {
                    "linkedin_member_id": lead.get("memberId"),
                    "campaign_id": lead.get("campaignId"),
                    "creative_id": lead.get("creativeId"),
                }
            }
        except Exception as e:
            logger.error("Failed to process LinkedIn webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid LinkedIn webhook format")

    async def _process_google_ads_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Google Ads Lead Form webhook"""
        try:
            lead = payload.get("lead", {})

            return {
                "email": lead.get("email"),
                "first_name": lead.get("first_name"),
                "last_name": lead.get("last_name"),
                "company": lead.get("company_name"),
                "phone": lead.get("phone_number"),
                "source": "google_ads",
                "campaign": lead.get("campaign_id"),
                "custom_fields": {
                    "google_lead_id": lead.get("lead_id"),
                    "campaign_id": lead.get("campaign_id"),
                    "ad_group_id": lead.get("ad_group_id"),
                    "keyword": lead.get("keyword"),
                }
            }
        except Exception as e:
            logger.error("Failed to process Google Ads webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid Google Ads webhook format")

    async def _process_webflow_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Webflow form submission webhook"""
        try:
            return {
                "email": payload.get("email"),
                "first_name": payload.get("name", "").split()[0] if payload.get("name") else payload.get("first-name"),
                "last_name": " ".join(payload.get("name", "").split()[1:]) if payload.get("name") and len(payload.get("name", "").split()) > 1 else payload.get("last-name"),
                "company": payload.get("company"),
                "phone": payload.get("phone"),
                "source": "webflow",
                "campaign": payload.get("site"),
                "custom_fields": {
                    "webflow_site_id": payload.get("site"),
                    "form_name": payload.get("name"),
                    "d": payload.get("d"),  # Webflow form data
                }
            }
        except Exception as e:
            logger.error("Failed to process Webflow webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid Webflow webhook format")

    async def _process_calendly_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Calendly event webhook"""
        try:
            event = payload.get("payload", {})
            invitee = event.get("invitee", {})

            return {
                "email": invitee.get("email"),
                "first_name": invitee.get("first_name"),
                "last_name": invitee.get("last_name"),
                "source": "calendly",
                "campaign": "meeting_booking",
                "custom_fields": {
                    "calendly_event_uri": event.get("uri"),
                    "event_type": event.get("event_type", {}).get("name"),
                    "scheduled_event_uri": event.get("scheduled_event", {}).get("uri"),
                    "meeting_start_time": event.get("scheduled_event", {}).get("start_time"),
                }
            }
        except Exception as e:
            logger.error("Failed to process Calendly webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid Calendly webhook format")

    async def _process_custom_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process custom webhook format"""
        try:
            # Flexible mapping for custom webhooks
            return {
                "email": payload.get("email") or payload.get("Email") or payload.get("EMAIL"),
                "first_name": payload.get("first_name") or payload.get("firstName") or payload.get("FirstName"),
                "last_name": payload.get("last_name") or payload.get("lastName") or payload.get("LastName"),
                "company": payload.get("company") or payload.get("Company") or payload.get("organization"),
                "phone": payload.get("phone") or payload.get("Phone") or payload.get("phoneNumber"),
                "source": "custom",
                "campaign": payload.get("campaign") or payload.get("source") or payload.get("utm_campaign"),
                "utm_params": {
                    "utm_source": payload.get("utm_source"),
                    "utm_medium": payload.get("utm_medium"),
                    "utm_campaign": payload.get("utm_campaign"),
                    "utm_term": payload.get("utm_term"),
                    "utm_content": payload.get("utm_content"),
                },
                "custom_fields": payload
            }
        except Exception as e:
            logger.error("Failed to process custom webhook", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid custom webhook format")

    def _verify_signature(self, source: str, payload: Dict[str, Any], signature: str) -> bool:
        """Verify webhook signature for security"""
        try:
            # Get the secret for this source (in production, store in secure config)
            secrets = {
                "hubspot": getattr(settings, 'hubspot_webhook_secret', ''),
                "typeform": getattr(settings, 'typeform_webhook_secret', ''),
                "facebook": getattr(settings, 'facebook_webhook_secret', ''),
                # Add more as needed
            }

            secret = secrets.get(source)
            if not secret:
                logger.warning("No webhook secret configured", source=source)
                return True  # Skip verification if no secret configured

            # Create expected signature
            payload_str = json.dumps(payload, sort_keys=True)
            expected_signature = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error("Signature verification failed", source=source, error=str(e))
            return False