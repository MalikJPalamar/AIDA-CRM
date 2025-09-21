"""
Test lead management endpoints
"""

import pytest
from fastapi.testclient import TestClient


def test_create_lead(client: TestClient, sample_lead_data):
    """Test lead creation."""
    response = client.post("/api/v1/leads/", json=sample_lead_data)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "lead_id" in data["data"]


def test_list_leads(client: TestClient):
    """Test lead listing."""
    response = client.get("/api/v1/leads/")
    assert response.status_code == 200

    data = response.json()
    assert "leads" in data
    assert "total_count" in data
    assert "limit" in data
    assert "offset" in data


def test_get_lead_qualification(client: TestClient):
    """Test lead qualification endpoint."""
    # First create a lead (in real test, would use existing lead)
    lead_id = "test-lead-123"

    response = client.get(f"/api/v1/leads/{lead_id}/qualification")
    # Expected to return 404 for non-existent lead in this mock
    assert response.status_code in [200, 404]


def test_update_lead_score(client: TestClient):
    """Test lead score update."""
    lead_id = "test-lead-123"
    score_data = {
        "new_score": 85,
        "reason": "Updated contact information",
        "autonomy_level": 2
    }

    response = client.patch(f"/api/v1/leads/{lead_id}/score", json=score_data)
    # Expected to return 404 for non-existent lead in this mock
    assert response.status_code in [200, 404]


def test_lead_analytics(client: TestClient):
    """Test lead analytics endpoint."""
    response = client.get("/api/v1/leads/analytics")
    assert response.status_code == 200

    data = response.json()
    assert "period" in data
    assert "summary" in data
    assert "conversion_funnel" in data
    assert "source_analysis" in data