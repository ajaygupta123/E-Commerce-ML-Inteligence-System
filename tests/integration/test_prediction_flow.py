"""Integration tests for prediction flow."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from src.api.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


@pytest.fixture
def mock_prediction_service():
    """Mock prediction service."""
    service = Mock()
    service.is_ready = True
    service.predict.return_value = {
        "predicted_discount": 25.5,
        "confidence_score": 0.85,
        "features": {"category": "Electronics", "actual_price": 100.0}
    }
    service.predict_with_explanation = Mock(return_value={
        "predicted_discount": 25.5,
        "confidence_score": 0.85,
        "features": {"category": "Electronics", "actual_price": 100.0},
        "explanation": {
            "shap_values": {"category": 0.5, "actual_price": 0.3},
            "base_value": 20.0
        }
    })
    return service


class TestPredictionFlow:
    """Test full prediction flow."""
    
    def test_predict_discount_success(self, client, mock_prediction_service):
        """Test successful prediction request."""
        with patch('src.api.dependencies.get_prediction_service', return_value=mock_prediction_service):
            response = client.post(
                "/v1/predict_discount",
                json={
                    "category": "Electronics",
                    "actual_price": 100.0,
                    "rating": 4.5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "predicted_discount" in data
            assert "confidence_score" in data
            assert data["predicted_discount"] == 25.5
            assert data["confidence_score"] == 0.85
    
    def test_predict_discount_missing_category(self, client):
        """Test prediction with missing required field."""
        response = client.post(
            "/v1/predict_discount",
            json={
                "actual_price": 100.0
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_predict_discount_invalid_price(self, client):
        """Test prediction with invalid price."""
        response = client.post(
            "/v1/predict_discount",
            json={
                "category": "Electronics",
                "actual_price": -10.0
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_predict_discount_model_not_loaded(self, client):
        """Test prediction when model is not loaded."""
        mock_service = Mock()
        mock_service.is_ready = False
        
        with patch('src.api.dependencies.get_prediction_service', return_value=mock_service):
            response = client.post(
                "/v1/predict_discount",
                json={
                    "category": "Electronics",
                    "actual_price": 100.0
                }
            )
            
            # Should return 503 or 500
            assert response.status_code in [500, 503]
    
    def test_explain_prediction_success(self, client, mock_prediction_service):
        """Test successful explanation request."""
        mock_prediction_service.predict.return_value = {
            "predicted_discount": 25.5,
            "confidence_score": 0.85,
            "features": {"category": "Electronics", "actual_price": 100.0},
            "explanation": {
                "shap_values": {"category": 0.5, "actual_price": 0.3},
                "base_value": 20.0,
                "feature_importance": {"category": 0.5, "actual_price": 0.3}
            }
        }
        
        with patch('src.api.dependencies.get_prediction_service', return_value=mock_prediction_service):
            response = client.post(
                "/v1/explain",
                json={
                    "category": "Electronics",
                    "actual_price": 100.0
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "predicted_discount" in data
            assert "explanation" in data
            assert "shap_values" in data["explanation"]
    
    def test_explain_prediction_model_not_loaded(self, client):
        """Test explanation when model is not loaded."""
        mock_service = Mock()
        mock_service.is_ready = False
        
        with patch('src.api.dependencies.get_prediction_service', return_value=mock_service):
            response = client.post(
                "/v1/explain",
                json={
                    "category": "Electronics",
                    "actual_price": 100.0
                }
            )
            
            assert response.status_code in [500, 503]



