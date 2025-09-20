"""
AIDA-CRM Webhook API Endpoints
Multi-channel lead capture from external platforms
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.database import get_db
from ..services.lead_service import LeadService
from ..services.webhook_service import WebhookService

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/capture/{source}")
async def capture_webhook(
    source: str,
    payload: Dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_signature: str = Header(None, alias="X-Signature"),
    x_hub_signature: str = Header(None, alias="X-Hub-Signature"),
    x_typeform_signature: str = Header(None, alias="X-Typeform-Signature"),
):
    """
    Universal webhook endpoint for capturing leads from various sources

    Supported sources:
    - hubspot: HubSpot form submissions
    - salesforce: Salesforce lead webhooks
    - zapier: Zapier webhook integration
    - typeform: Typeform submission webhooks
    - facebook: Facebook Lead Ads
    - linkedin: LinkedIn Lead Gen Forms
    - google_ads: Google Ads Lead Forms
    - webflow: Webflow form submissions
    - calendly: Calendly event bookings
    - custom: Custom webhook format
    """
    try:
        # Initialize services
        lead_service = LeadService(db)
        webhook_service = WebhookService(lead_service)

        # Determine signature based on source
        signature = x_signature or x_hub_signature or x_typeform_signature

        # Process the webhook
        result = await webhook_service.process_webhook(
            source=source,
            payload=payload,
            signature=signature,
            request=request
        )

        logger.info(
            "Webhook captured successfully",
            source=source,
            lead_id=result.get("lead_id"),
            qualification_score=result.get("qualification_score")
        )

        return {
            "status": "success",
            "message": f"Lead captured from {source}",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook capture failed", source=source, error=str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/sources")
async def list_webhook_sources():
    """List all supported webhook sources and their requirements"""
    return {
        "sources": {
            "hubspot": {
                "description": "HubSpot form submissions",
                "required_fields": ["email"],
                "optional_fields": ["firstname", "lastname", "company", "phone"],
                "signature_header": "X-HubSpot-Signature",
                "documentation": "https://developers.hubspot.com/docs/api/webhooks"
            },
            "salesforce": {
                "description": "Salesforce lead webhooks",
                "required_fields": ["Email"],
                "optional_fields": ["FirstName", "LastName", "Company", "Phone"],
                "signature_header": "X-Signature",
                "documentation": "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_understanding_web_service_outbound_messages.htm"
            },
            "zapier": {
                "description": "Zapier webhook integration",
                "required_fields": ["email"],
                "optional_fields": ["first_name", "last_name", "company", "phone", "utm_*"],
                "signature_header": "X-Signature",
                "documentation": "https://zapier.com/apps/webhook/help"
            },
            "typeform": {
                "description": "Typeform submission webhooks",
                "required_fields": ["form_response.answers"],
                "optional_fields": ["email", "name", "company", "phone"],
                "signature_header": "X-Typeform-Signature",
                "documentation": "https://developer.typeform.com/webhooks/"
            },
            "facebook": {
                "description": "Facebook Lead Ads",
                "required_fields": ["entry.changes.value"],
                "optional_fields": ["email", "first_name", "last_name", "phone_number"],
                "signature_header": "X-Hub-Signature",
                "documentation": "https://developers.facebook.com/docs/marketing-api/guides/lead-ads/"
            },
            "linkedin": {
                "description": "LinkedIn Lead Gen Forms",
                "required_fields": ["leadGenFormResponse"],
                "optional_fields": ["emailAddress", "firstName", "lastName", "companyName"],
                "signature_header": "X-Signature",
                "documentation": "https://docs.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/leads"
            },
            "google_ads": {
                "description": "Google Ads Lead Forms",
                "required_fields": ["lead"],
                "optional_fields": ["email", "first_name", "last_name", "company_name"],
                "signature_header": "X-Signature",
                "documentation": "https://developers.google.com/google-ads/api/docs/lead-form-extensions"
            },
            "webflow": {
                "description": "Webflow form submissions",
                "required_fields": ["email"],
                "optional_fields": ["name", "company", "phone"],
                "signature_header": "X-Signature",
                "documentation": "https://university.webflow.com/lesson/intro-to-zapier-and-webflow"
            },
            "calendly": {
                "description": "Calendly event bookings",
                "required_fields": ["payload.invitee"],
                "optional_fields": ["email", "first_name", "last_name"],
                "signature_header": "X-Signature",
                "documentation": "https://help.calendly.com/hc/en-us/articles/223147027-Webhook-subscriptions"
            },
            "custom": {
                "description": "Custom webhook format with flexible field mapping",
                "required_fields": ["email"],
                "optional_fields": ["first_name", "last_name", "company", "phone", "any_custom_field"],
                "signature_header": "X-Signature",
                "documentation": "Custom implementation - contact support for details"
            }
        },
        "webhook_url_format": "/api/v1/webhooks/capture/{source}",
        "example_urls": {
            "hubspot": "/api/v1/webhooks/capture/hubspot",
            "typeform": "/api/v1/webhooks/capture/typeform",
            "custom": "/api/v1/webhooks/capture/custom"
        }
    }


@router.post("/test/{source}")
async def test_webhook(
    source: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Test webhook processing without actually creating a lead
    Useful for debugging webhook integrations
    """
    try:
        lead_service = LeadService(db)
        webhook_service = WebhookService(lead_service)

        # Process webhook but don't save to database
        if source not in ["hubspot", "salesforce", "zapier", "typeform", "facebook",
                         "linkedin", "google_ads", "webflow", "calendly", "custom"]:
            raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

        # Extract lead data without saving
        handler_map = {
            "hubspot": webhook_service._process_hubspot_webhook,
            "salesforce": webhook_service._process_salesforce_webhook,
            "zapier": webhook_service._process_zapier_webhook,
            "typeform": webhook_service._process_typeform_webhook,
            "facebook": webhook_service._process_facebook_webhook,
            "linkedin": webhook_service._process_linkedin_webhook,
            "google_ads": webhook_service._process_google_ads_webhook,
            "webflow": webhook_service._process_webflow_webhook,
            "calendly": webhook_service._process_calendly_webhook,
            "custom": webhook_service._process_custom_webhook,
        }

        handler = handler_map[source]
        lead_data = await handler(payload)

        return {
            "status": "success",
            "message": f"Webhook test successful for {source}",
            "extracted_data": lead_data,
            "note": "This is a test - no lead was actually created"
        }

    except Exception as e:
        logger.error("Webhook test failed", source=source, error=str(e))
        return {
            "status": "error",
            "message": f"Webhook test failed: {str(e)}",
            "source": source,
            "payload": payload
        }