"""
Test health endpoints
"""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_health_detailed(client: TestClient):
    """Test detailed health check endpoint."""
    response = client.get("/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "system_info" in data

    # Check service statuses
    services = data["services"]
    assert "database" in services
    assert "nats" in services
    assert "ai_service" in services


def test_readiness_check(client: TestClient):
    """Test readiness endpoint."""
    response = client.get("/health/ready")
    assert response.status_code in [200, 503]  # May not be ready in test environment

    data = response.json()
    assert "status" in data
    assert "checks" in data


def test_liveness_check(client: TestClient):
    """Test liveness endpoint."""
    response = client.get("/health/live")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "alive"
    assert "uptime" in data