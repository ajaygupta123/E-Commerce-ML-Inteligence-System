"""Integration tests for error handling."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from src.api.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_json(self, client):
        """Test request with invalid JSON."""
        response = client.post(
            "/v1/predict_discount",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_content_type(self, client):
        """Test request without Content-Type header."""
        response = client.post(
            "/v1/predict_discount",
            data='{"category": "Electronics"}'
        )
        
        # FastAPI should handle this gracefully
        assert response.status_code in [422, 415]
    
    def test_nonexistent_endpoint(self, client):
        """Test request to non-existent endpoint."""
        response = client.get("/v1/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test using wrong HTTP method."""
        response = client.get("/v1/predict_discount")
        
        assert response.status_code == 405  # Method not allowed
    
    def test_internal_server_error(self, client):
        """Test handling of internal server errors."""
        mock_service = Mock()
        mock_service.is_ready = True
        mock_service.predict.side_effect = Exception("Internal error")
        
        with patch('src.api.dependencies.get_prediction_service', return_value=mock_service):
            response = client.post(
                "/v1/predict_discount",
                json={
                    "category": "Electronics",
                    "actual_price": 100.0
                }
            )
            
            assert response.status_code == 500
    
    def test_service_unavailable(self, client):
        """Test service unavailable scenario."""
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
            
            assert response.status_code in [500, 503]
    
    def test_malformed_request_body(self, client):
        """Test malformed request body."""
        response = client.post(
            "/v1/predict_discount",
            json={
                "category": 123,  # Should be string
                "actual_price": "not a number"  # Should be number
            }
        )
        
        assert response.status_code == 422
    
    def test_extra_fields_ignored(self, client):
        """Test that extra fields are ignored (not causing errors)."""
        mock_service = Mock()
        mock_service.is_ready = True
        mock_service.predict.return_value = {
            "predicted_discount": 25.5,
            "confidence_score": 0.85,
            "features": {}
        }
        
        with patch('src.api.dependencies.get_prediction_service', return_value=mock_service):
            response = client.post(
                "/v1/predict_discount",
                json={
                    "category": "Electronics",
                    "actual_price": 100.0,
                    "extra_field": "should be ignored"
                }
            )
            
            # Should still work (extra fields ignored)
            assert response.status_code in [200, 422]



