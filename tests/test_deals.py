"""
Test deal management endpoints
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


def test_create_deal_from_lead(client: TestClient):
    """Test deal creation from lead."""
    deal_data = {
        "lead_id": str(uuid4()),
        "title": "Test Deal",
        "value": 25000,
        "autonomy_level": 2
    }

    response = client.post("/api/v1/deals/create-from-lead", json=deal_data)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "data" in data


def test_progress_deal(client: TestClient):
    """Test deal progression."""
    deal_id = str(uuid4())
    user_id = str(uuid4())

    progress_data = {
        "new_stage": "qualified",
        "reason": "Customer showed strong interest",
        "autonomy_level": 3
    }

    response = client.post(
        f"/api/v1/deals/{deal_id}/progress?user_id={user_id}",
        json=progress_data
    )
    # Expected to work with mock data
    assert response.status_code == 200


def test_update_deal_value(client: TestClient):
    """Test deal value update."""
    deal_id = str(uuid4())

    value_data = {
        "new_value": 35000,
        "reason": "Added additional services",
        "autonomy_level": 2
    }

    response = client.patch(f"/api/v1/deals/{deal_id}/value", json=value_data)
    assert response.status_code == 200


def test_list_deals(client: TestClient):
    """Test deal listing."""
    response = client.get("/api/v1/deals/")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_get_pipeline_analytics(client: TestClient):
    """Test pipeline analytics."""
    response = client.get("/api/v1/deals/pipeline/analytics")
    assert response.status_code == 200

    data = response.json()
    assert "period" in data
    assert "summary" in data
    assert "forecast" in data


def test_get_stage_definitions(client: TestClient):
    """Test stage definitions endpoint."""
    response = client.get("/api/v1/deals/stages/definitions")
    assert response.status_code == 200

    data = response.json()
    assert "stages" in data
    assert "autonomy_guidelines" in data

    # Check required stages exist
    stages = data["stages"]
    required_stages = ["prospect", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]
    for stage in required_stages:
        assert stage in stages


def test_add_deal_note(client: TestClient):
    """Test adding note to deal."""
    deal_id = str(uuid4())
    user_id = str(uuid4())

    note_data = {
        "note": "Customer requested demo scheduling",
        "note_type": "meeting"
    }

    response = client.post(
        f"/api/v1/deals/{deal_id}/notes?user_id={user_id}",
        json=note_data
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "note_id" in data