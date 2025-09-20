"""
AIDA-CRM Edge API Rate Limiting Middleware
"""

import time
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from ..core.config import settings

logger = structlog.get_logger()


class InMemoryRateLimiter:
    """Simple in-memory rate limiter using sliding window"""

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed within rate limit"""
        now = time.time()
        window_start = now - window

        # Clean old requests outside the window
        while self.requests[key] and self.requests[key][0] < window_start:
            self.requests[key].popleft()

        # Check if we're under the limit
        if len(self.requests[key]) < limit:
            self.requests[key].append(now)
            return True

        return False

    def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests in the current window"""
        now = time.time()
        window_start = now - window

        # Clean old requests
        while self.requests[key] and self.requests[key][0] < window_start:
            self.requests[key].popleft()

        return max(0, limit - len(self.requests[key]))

    def get_reset_time(self, key: str, window: int) -> Optional[float]:
        """Get when the rate limit resets"""
        if not self.requests[key]:
            return None

        oldest_request = self.requests[key][0]
        return oldest_request + window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(self, app, limiter: Optional[InMemoryRateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter()
        self.enabled = settings.rate_limit_enabled
        self.requests_per_window = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_period

    def get_client_id(self, request: Request) -> str:
        """Extract client identifier for rate limiting"""
        # Try to get user ID from auth token first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from ..core.security import verify_token
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                return f"user:{payload.get('sub', 'unknown')}"
            except Exception:
                pass

        # Fall back to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        client_host = getattr(request.client, 'host', 'unknown')
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next):
        """Process rate limiting"""
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        client_id = self.get_client_id(request)

        # Check rate limit
        if not self.limiter.is_allowed(
            client_id, self.requests_per_window, self.window_seconds
        ):
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                path=request.url.path,
                method=request.method
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(
                        self.limiter.get_reset_time(client_id, self.window_seconds) or time.time()
                    )),
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.limiter.get_remaining(
            client_id, self.requests_per_window, self.window_seconds
        )
        reset_time = self.limiter.get_reset_time(client_id, self.window_seconds)

        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if reset_time:
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))

        return response