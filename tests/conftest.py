"""
Test configuration and fixtures for AIDA-CRM
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from core.app.main import app
from core.app.core.database import Base, get_db

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(test_db: AsyncSession):
    """Create test client with database override."""
    def get_test_db():
        return test_db

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_lead_data():
    """Sample lead data for testing."""
    return {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "company": "Test Corp",
        "phone": "+1234567890",
        "source": "demo_request",
        "metadata": {
            "form_data": {"product_interest": "enterprise"},
            "utm_source": "google",
            "utm_campaign": "demo"
        }
    }


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing."""
    return {
        "type": "lead_capture",
        "source": "hubspot",
        "timestamp": "2024-01-15T10:30:00Z",
        "data": {
            "email": "webhook@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "company": "Webhook Corp",
            "lead_source": "content_download"
        }
    }