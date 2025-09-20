"""
AIDA-CRM Core API Health Endpoints
"""

import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import structlog

from ..core.database import get_db
from ..services.nats_client import get_nats_client

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])

# Track service start time
start_time = time.time()


@router.get("/")
async def health_check():
    """Basic health check"""
    uptime = time.time() - start_time
    return {
        "status": "healthy",
        "service": "aida-core",
        "version": "0.2.0",
        "uptime_seconds": uptime,
        "timestamp": time.time()
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check with dependency validation"""
    uptime = time.time() - start_time
    services = {}

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception as e:
        logger.warning("Database health check failed", error=str(e))
        services["database"] = "unhealthy"

    # Check NATS
    try:
        nats_client = await get_nats_client()
        if await nats_client.health_check():
            services["nats"] = "healthy"
        else:
            services["nats"] = "unhealthy"
    except Exception as e:
        logger.warning("NATS health check failed", error=str(e))
        services["nats"] = "unhealthy"

    # Determine overall status
    all_healthy = all(status == "healthy" for status in services.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "service": "aida-core",
        "version": "0.2.0",
        "uptime_seconds": uptime,
        "services": services,
        "timestamp": time.time()
    }


@router.get("/live")
async def liveness_check():
    """Liveness check - basic service responsiveness"""
    return {
        "status": "alive",
        "service": "aida-core",
        "timestamp": time.time()
    }