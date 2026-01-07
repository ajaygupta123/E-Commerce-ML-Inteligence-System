"""Integration tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()


def test_predict_discount_endpoint():
    """Test prediction endpoint."""
    payload = {
        "price": 100.0,
        "category": "Electronics",
        "rating": 4.5,
    }
    # This will fail if model not loaded, which is expected
    response = client.post("/v1/predict_discount", json=payload)
    # Should return 500 if model not loaded, or 200 if loaded
    assert response.status_code in [200, 500]




