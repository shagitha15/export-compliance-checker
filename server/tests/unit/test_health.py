"""
Unit tests for the Health Check endpoint and controller.
"""

from fastapi.testclient import TestClient


def test_health_check_endpoint(client: TestClient):
    """
    Test GET /api/v1/health returns 200 and healthy status.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert "data" in body
    health_payload = body["data"]
    assert health_payload["status"] in ["healthy", "degraded"]
    assert "version" in health_payload
    assert "environment" in health_payload
    assert "timestamp" in health_payload
    assert "components" in health_payload


def test_root_endpoint(client: TestClient):
    """
    Test GET / returns project metadata.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert data["api_v1_prefix"] == "/api/v1"
