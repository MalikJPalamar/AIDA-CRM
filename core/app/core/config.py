"""
AIDA-CRM Core API Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "AIDA-CRM Core API"
    version: str = "0.2.0"
    debug: bool = False
    environment: str = "production"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API Configuration
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str

    # NATS Configuration
    nats_url: str = "nats://localhost:4222"

    # Vector Database
    chroma_url: str = "http://localhost:8000"
    chroma_auth_token: Optional[str] = None

    # DuckDB Analytics
    duckdb_path: str = "/data/analytics.duckdb"

    # LLM Configuration
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "moonshotai/kimi-k2"

    # Monitoring
    prometheus_enabled: bool = True
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Autonomy Configuration
    default_autonomy_level: int = 1
    max_autonomy_level: int = 5
    confidence_threshold: float = 0.8

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()