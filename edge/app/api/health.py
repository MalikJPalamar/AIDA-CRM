"""
AIDA-CRM Edge API Health Endpoints
"""

import time
import httpx
import asyncio
from typing import Dict
from fastapi import APIRouter, Depends
import structlog

from ..core.config import settings
from ..models.responses import HealthCheckResponse, ResponseStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])

# Track service start time
start_time = time.time()


async def check_core_api() -> str:
    """Check core API health"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.core_api_url}/health")
            return "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        logger.warning("Core API health check failed", error=str(e))
        return "unhealthy"


async def check_nats() -> str:
    """Check NATS connection"""
    try:
        import nats
        nc = await nats.connect(settings.nats_url, connect_timeout=2)
        await nc.close()
        return "healthy"
    except Exception as e:
        logger.warning("NATS health check failed", error=str(e))
        return "unhealthy"


@router.get("/", response_model=HealthCheckResponse)
async def health_check():
    """Basic health check endpoint"""
    uptime = time.time() - start_time

    return HealthCheckResponse(
        status=ResponseStatus.SUCCESS,
        message="Edge API is healthy",
        version=settings.version,
        uptime_seconds=uptime,
        services={"edge_api": "healthy"}
    )


@router.get("/ready", response_model=HealthCheckResponse)
async def readiness_check():
    """Readiness check with dependency validation"""
    uptime = time.time() - start_time

    # Check all dependencies concurrently
    services_checks = await asyncio.gather(
        check_core_api(),
        check_nats(),
        return_exceptions=True
    )

    services = {
        "edge_api": "healthy",
        "core_api": services_checks[0] if isinstance(services_checks[0], str) else "unhealthy",
        "nats": services_checks[1] if isinstance(services_checks[1], str) else "unhealthy",
    }

    # Determine overall status
    all_healthy = all(status == "healthy" for status in services.values())
    status = ResponseStatus.SUCCESS if all_healthy else ResponseStatus.ERROR
    message = "All systems ready" if all_healthy else "Some dependencies unhealthy"

    return HealthCheckResponse(
        status=status,
        message=message,
        version=settings.version,
        uptime_seconds=uptime,
        services=services
    )


@router.get("/live", response_model=HealthCheckResponse)
async def liveness_check():
    """Liveness check - basic service responsiveness"""
    uptime = time.time() - start_time

    return HealthCheckResponse(
        status=ResponseStatus.SUCCESS,
        message="Edge API is alive",
        version=settings.version,
        uptime_seconds=uptime,
        services={"edge_api": "alive"}
    )