"""
AIDA-CRM Core API Main Application
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
import structlog

from .core.config import settings
from .core.database import init_db, close_db
from .services.nats_client import initialize_nats, close_nats
from .api import health, leads, webhooks, communications, deals, customer_success

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting AIDA-CRM Core API", version=settings.version)

    # Initialize database
    await init_db()

    # Initialize NATS
    try:
        await initialize_nats(settings.nats_url)
    except Exception as e:
        logger.warning("Failed to initialize NATS", error=str(e))

    # Startup complete
    yield

    # Shutdown
    logger.info("Shutting down AIDA-CRM Core API")

    # Close NATS
    await close_nats()

    # Close database
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AIDA-CRM Core API - AI-Driven Autonomy CRM Platform",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect Prometheus metrics for all requests"""
    start_time = time.time()

    # Get endpoint from route
    endpoint = request.url.path
    method = request.method

    # Process request
    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    status_code = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

    # Add response headers
    response.headers["X-Response-Time"] = f"{duration:.3f}s"

    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()

    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown"
    )

    response = await call_next(request)

    duration = time.time() - start_time

    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )

    return response


# Include routers
app.include_router(health.router)
app.include_router(leads.router, prefix=settings.api_v1_prefix)
app.include_router(webhooks.router, prefix=settings.api_v1_prefix)
app.include_router(communications.router, prefix=settings.api_v1_prefix)
app.include_router(deals.router, prefix=settings.api_v1_prefix)
app.include_router(customer_success.router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.version,
        "status": "operational",
        "docs": "/docs" if settings.debug else "disabled",
        "environment": settings.environment
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    if not settings.prometheus_enabled:
        return {"detail": "Metrics not enabled"}

    return generate_latest()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )