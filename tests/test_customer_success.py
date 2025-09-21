"""
Test customer success endpoints
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


def test_initiate_onboarding(client: TestClient):
    """Test customer onboarding initiation."""
    onboarding_data = {
        "deal_id": str(uuid4()),
        "onboarding_type": "standard",
        "autonomy_level": 3
    }

    response = client.post("/api/v1/customer-success/onboarding/initiate", json=onboarding_data)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "data" in data


def test_get_health_score(client: TestClient):
    """Test customer health score calculation."""
    customer_id = str(uuid4())

    response = client.get(f"/api/v1/customer-success/health-score/{customer_id}")
    assert response.status_code == 200

    data = response.json()
    assert "customer_id" in data
    assert "health_score" in data
    assert "health_category" in data
    assert "risk_level" in data
    assert "churn_probability" in data


def test_get_expansion_opportunities(client: TestClient):
    """Test expansion opportunity identification."""
    customer_id = str(uuid4())

    response = client.get(f"/api/v1/customer-success/expansion-opportunities/{customer_id}")
    assert response.status_code == 200

    data = response.json()
    assert "customer_id" in data
    assert "expansion_potential" in data
    assert "total_opportunity_value" in data
    assert "opportunities" in data


def test_execute_retention_campaign(client: TestClient):
    """Test retention campaign execution."""
    campaign_data = {
        "customer_id": str(uuid4()),
        "campaign_type": "proactive",
        "risk_level": "medium",
        "autonomy_level": 2
    }

    response = client.post("/api/v1/customer-success/retention/campaign", json=campaign_data)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "data" in data


def test_get_analytics(client: TestClient):
    """Test customer success analytics."""
    response = client.get("/api/v1/customer-success/analytics")
    assert response.status_code == 200

    data = response.json()
    assert "period" in data
    assert "customer_metrics" in data
    assert "health_distribution" in data
    assert "retention_metrics" in data


def test_list_customers(client: TestClient):
    """Test customer listing with filters."""
    response = client.get("/api/v1/customer-success/customers")
    assert response.status_code == 200

    data = response.json()
    assert "customers" in data
    assert "total_count" in data

    # Test with filters
    response = client.get("/api/v1/customer-success/customers?health_category=good&limit=10")
    assert response.status_code == 200


def test_get_customer_timeline(client: TestClient):
    """Test customer timeline retrieval."""
    customer_id = str(uuid4())

    response = client.get(f"/api/v1/customer-success/customers/{customer_id}/timeline")
    assert response.status_code == 200

    data = response.json()
    assert "customer_id" in data
    assert "timeline" in data
    assert "total_events" in data


def test_recalculate_health_score(client: TestClient):
    """Test manual health score recalculation."""
    customer_id = str(uuid4())

    response = client.post(f"/api/v1/customer-success/customers/{customer_id}/health-score/recalculate")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "data" in data


def test_get_playbooks(client: TestClient):
    """Test customer success playbooks."""
    response = client.get("/api/v1/customer-success/playbooks")
    assert response.status_code == 200

    data = response.json()
    assert "playbooks" in data
    assert "total_categories" in data
    assert "recommendations" in data

    # Check required playbook categories
    playbooks = data["playbooks"]
    assert "onboarding" in playbooks
    assert "retention" in playbooks
    assert "expansion" in playbooks


def test_get_benchmarks(client: TestClient):
    """Test customer success benchmarks."""
    response = client.get("/api/v1/customer-success/metrics/benchmarks")
    assert response.status_code == 200

    data = response.json()
    assert "benchmarks" in data
    assert "last_updated" in data

    # Check benchmark categories
    benchmarks = data["benchmarks"]
    assert "health_scores" in benchmarks
    assert "retention_rates" in benchmarks
    assert "expansion_rates" in benchmarks


def test_create_intervention(client: TestClient):
    """Test customer intervention creation."""
    customer_id = str(uuid4())

    intervention_data = {
        "intervention_type": "retention_call",
        "priority": "high",
        "notes": "Customer showing signs of churn risk"
    }

    response = client.post(
        f"/api/v1/customer-success/customers/{customer_id}/interventions",
        json=intervention_data
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "data" in data