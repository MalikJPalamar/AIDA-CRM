"""
AIDA-CRM Edge API Authentication Endpoints
"""

import httpx
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
import structlog

from ..core.config import settings
from ..core.security import create_access_token, get_current_user
from ..models.requests import AuthRequest, TokenRefreshRequest
from ..models.responses import AuthResponse, ResponseStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/login", response_model=AuthResponse)
async def login(auth_request: AuthRequest):
    """Authenticate user and return JWT token"""
    try:
        # Forward authentication to core API
        async with httpx.AsyncClient(timeout=settings.core_api_timeout) as client:
            response = await client.post(
                f"{settings.core_api_url}/api/v1/auth/login",
                json=auth_request.model_dump()
            )

            if response.status_code != 200:
                logger.warning(
                    "Authentication failed",
                    email=auth_request.email,
                    status_code=response.status_code
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )

            user_data = response.json()

        # Create edge API JWT token
        access_token = create_access_token(
            data={"sub": user_data["user_id"], "email": auth_request.email}
        )

        logger.info("User authenticated successfully", user_id=user_data["user_id"])

        return AuthResponse(
            status=ResponseStatus.SUCCESS,
            message="Authentication successful",
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user_id=user_data["user_id"]
        )

    except httpx.RequestError as e:
        logger.error("Core API connection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable"
        )
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(refresh_request: TokenRefreshRequest):
    """Refresh JWT token"""
    try:
        # Forward refresh request to core API
        async with httpx.AsyncClient(timeout=settings.core_api_timeout) as client:
            response = await client.post(
                f"{settings.core_api_url}/api/v1/auth/refresh",
                json=refresh_request.model_dump()
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            token_data = response.json()

        # Create new edge API JWT token
        access_token = create_access_token(
            data={"sub": token_data["user_id"], "email": token_data.get("email")}
        )

        return AuthResponse(
            status=ResponseStatus.SUCCESS,
            message="Token refreshed successfully",
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user_id=token_data["user_id"]
        )

    except httpx.RequestError as e:
        logger.error("Core API connection failed during refresh", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token refresh service temporarily unavailable"
        )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return {
        "user_id": current_user.get("sub"),
        "email": current_user.get("email"),
        "authenticated": True
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (invalidate token)"""
    # In a full implementation, you would:
    # 1. Add token to blacklist
    # 2. Notify core API of logout
    # 3. Clear any cached sessions

    logger.info("User logged out", user_id=current_user.get("sub"))

    return {
        "status": "success",
        "message": "Logged out successfully"
    }