"""
AIDA-CRM Edge API Request Models
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


class LeadCaptureRequest(BaseModel):
    """Request model for lead capture"""
    email: EmailStr = Field(..., description="Lead email address")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    company: Optional[str] = Field(None, max_length=200, description="Company name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    source: Optional[str] = Field("web", description="Lead source")
    campaign: Optional[str] = Field(None, description="Marketing campaign")
    utm_params: Optional[Dict[str, str]] = Field(None, description="UTM parameters")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom lead data")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme Corp",
                "phone": "+1-555-123-4567",
                "source": "web",
                "campaign": "q4-promotion",
                "utm_params": {
                    "utm_source": "google",
                    "utm_medium": "cpc",
                    "utm_campaign": "q4-promotion"
                }
            }
        }


class AuthRequest(BaseModel):
    """Authentication request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")


class TokenRefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str = Field(..., description="Refresh token")


class HealthCheckRequest(BaseModel):
    """Health check request for internal monitoring"""
    service: Optional[str] = Field(None, description="Service name to check")
    deep: bool = Field(False, description="Perform deep health check")


class WebhookRequest(BaseModel):
    """Generic webhook request"""
    event_type: str = Field(..., description="Type of webhook event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Webhook payload data")
    signature: Optional[str] = Field(None, description="Webhook signature for verification")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "lead.form_submitted",
                "data": {
                    "form_id": "contact-form-1",
                    "email": "prospect@example.com",
                    "name": "Jane Smith"
                }
            }
        }