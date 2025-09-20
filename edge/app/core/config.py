"""
AIDA-CRM Edge API Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "AIDA-CRM Edge API"
    version: str = "0.2.0"
    debug: bool = False
    environment: str = "production"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    max_request_size: int = 10 * 1024 * 1024  # 10MB

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds

    # Core Services
    core_api_url: str = "http://localhost:8001"
    core_api_timeout: int = 30

    # NATS Configuration
    nats_url: str = "nats://localhost:4222"
    nats_timeout: int = 10

    # Database (for session storage)
    redis_url: Optional[str] = None

    # Monitoring
    prometheus_enabled: bool = True

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()