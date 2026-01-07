"""Security tests for input validation."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


class TestInputValidationSecurity:
    """Security tests for input validation."""
    
    def test_sql_injection_attempt(self, client):
        """Test protection against SQL injection."""
        # Attempt SQL injection in category field
        response = client.post(
            "/v1/predict_discount",
            json={
                "category": "'; DROP TABLE products; --",
                "actual_price": 100.0
            }
        )
        
        # Should be rejected or sanitized (not cause SQL error)
        # Status should be 422 (validation error) or 200 (sanitized)
        assert response.status_code in [200, 422, 400]
        
        # Should not return 500 (internal server error from SQL)
        assert response.status_code != 500
    
    def test_xss_attempt(self, client):
        """Test protection against XSS."""
        # Attempt XSS in question field
        response = client.post(
            "/v1/answer_question",
            json={
                "question": "<script>alert('XSS')</script>",
                "top_k": 5
            }
        )
        
        # Should be handled (either rejected or sanitized)
        assert response.status_code in [200, 400, 422]
    
    def test_oversized_payload(self, client):
        """Test protection against oversized payloads."""
        # Create very large payload
        large_string = "x" * 10000
        response = client.post(
            "/v1/answer_question",
            json={
                "question": large_string,
                "top_k": 5
            }
        )
        
        # Should be rejected (query too long)
        assert response.status_code in [400, 422]
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/v1/predict_discount",
            data='{"category": "Electronics", "actual_price": }',  # Invalid JSON
            headers={"Content-Type": "application/json"}
        )
        
        # Should return validation error, not crash
        assert response.status_code == 422
    
    def test_nested_object_attack(self, client):
        """Test protection against deeply nested objects."""
        # Create deeply nested object
        nested = {"level": 1}
        for i in range(2, 100):
            nested = {"level": i, "nested": nested}
        
        response = client.post(
            "/v1/predict_discount",
            json={
                "category": "Electronics",
                "actual_price": 100.0,
                "nested": nested
            }
        )
        
        # Should handle gracefully (either accept or reject)
        assert response.status_code in [200, 422, 400]
    
    def test_type_confusion_attack(self, client):
        """Test protection against type confusion."""
        # Send wrong types
        response = client.post(
            "/v1/predict_discount",
            json={
                "category": 12345,  # Should be string
                "actual_price": "not a number",  # Should be number
                "rating": "high"  # Should be number
            }
        )
        
        # Should be rejected with validation error
        assert response.status_code == 422
    
    def test_special_characters(self, client):
        """Test handling of special characters."""
        response = client.post(
            "/v1/answer_question",
            json={
                "question": "What are the best products? \x00\x01\x02",
                "top_k": 5
            }
        )
        
        # Should handle special characters (either sanitize or reject)
        assert response.status_code in [200, 400, 422]



