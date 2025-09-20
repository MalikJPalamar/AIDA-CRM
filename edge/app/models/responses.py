"""
AIDA-CRM Edge API Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    """Standard response statuses"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


class BaseResponse(BaseModel):
    """Base response model"""
    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LeadCaptureResponse(BaseResponse):
    """Response for lead capture"""
    lead_id: Optional[str] = Field(None, description="Generated lead ID")
    qualification_score: Optional[float] = Field(None, ge=0, le=1, description="AI qualification score")
    next_actions: Optional[List[str]] = Field(None, description="Suggested next actions")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Lead captured successfully",
                "lead_id": "lead_abc123",
                "qualification_score": 0.85,
                "next_actions": ["send_welcome_email", "assign_to_sales"]
            }
        }


class AuthResponse(BaseResponse):
    """Authentication response"""
    access_token: Optional[str] = Field(None, description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiration in seconds")
    user_id: Optional[str] = Field(None, description="User ID")


class HealthCheckResponse(BaseResponse):
    """Health check response"""
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    services: Dict[str, str] = Field(..., description="Dependent service statuses")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "All systems operational",
                "version": "0.2.0",
                "uptime_seconds": 3600.5,
                "services": {
                    "core_api": "healthy",
                    "nats": "healthy",
                    "database": "healthy"
                }
            }
        }


class ErrorResponse(BaseResponse):
    """Error response"""
    error_code: Optional[str] = Field(None, description="Specific error code")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Validation failed",
                "error_code": "VALIDATION_ERROR",
                "error_details": {
                    "field": "email",
                    "issue": "Invalid email format"
                }
            }
        }


class MetricsResponse(BaseModel):
    """Metrics response for monitoring"""
    requests_total: int = Field(..., description="Total requests processed")
    requests_per_second: float = Field(..., description="Current RPS")
    error_rate: float = Field(..., ge=0, le=1, description="Error rate (0-1)")
    average_response_time_ms: float = Field(..., description="Average response time")
    active_connections: int = Field(..., description="Current active connections")

    class Config:
        json_schema_extra = {
            "example": {
                "requests_total": 15420,
                "requests_per_second": 12.5,
                "error_rate": 0.02,
                "average_response_time_ms": 150.5,
                "active_connections": 45
            }
        }