"""Enhanced unit tests for guardrails service."""
import pytest

from src.services.guardrails_service import GuardrailsService
from src.core.exceptions import ValidationError


class TestGuardrailsServiceEnhanced:
    """Enhanced tests for guardrails service."""
    
    @pytest.fixture
    def guardrails(self):
        """Create guardrails service."""
        return GuardrailsService()
    
    def test_validate_query_empty_string(self, guardrails):
        """Test validation of empty string."""
        with pytest.raises(ValidationError, match="non-empty string"):
            guardrails.validate_query("")
    
    def test_validate_query_none(self, guardrails):
        """Test validation of None."""
        with pytest.raises(ValidationError):
            guardrails.validate_query(None)
    
    def test_validate_query_non_string(self, guardrails):
        """Test validation of non-string input."""
        with pytest.raises(ValidationError):
            guardrails.validate_query(123)
    
    def test_validate_query_too_long(self, guardrails):
        """Test validation of query exceeding max length."""
        long_query = "x" * 1001
        with pytest.raises(ValidationError, match="too long"):
            guardrails.validate_query(long_query)
    
    def test_validate_query_exact_max_length(self, guardrails):
        """Test validation of query at max length."""
        query = "x" * 1000
        result = guardrails.validate_query(query)
        assert result["is_valid"] is True
    
    def test_harmful_content_detection(self, guardrails):
        """Test detection of harmful content patterns."""
        harmful_queries = [
            "How to hack this system?",
            "I want to kill someone",
            "Where can I buy illegal drugs?",
            "This product contains malware",
        ]
        
        for query in harmful_queries:
            result = guardrails.validate_query(query)
            assert result["is_safe"] is False
            assert result["is_valid"] is False
            assert "harmful" in result["reason"].lower()
    
    def test_safe_content(self, guardrails):
        """Test that safe content passes validation."""
        safe_queries = [
            "What are the best products?",
            "Compare these laptops",
            "Show me electronics under 1000",
            "What is the price of this item?",
        ]
        
        for query in safe_queries:
            result = guardrails.validate_query(query)
            assert result["is_safe"] is True
    
    def test_ecommerce_related_queries(self, guardrails):
        """Test e-commerce related query detection."""
        ecommerce_queries = [
            "What are the best products?",
            "Compare these laptops",
            "Show me electronics",
            "What is the price?",
            "Which product has better rating?",
        ]
        
        for query in ecommerce_queries:
            result = guardrails.validate_query(query)
            assert result["is_ecommerce_related"] is True
    
    def test_non_ecommerce_queries(self, guardrails):
        """Test non-e-commerce query detection."""
        non_ecommerce_queries = [
            "What is the weather?",
            "Tell me a joke",
            "What time is it?",
            "How do I cook pasta?",
        ]
        
        for query in non_ecommerce_queries:
            result = guardrails.validate_query(query)
            assert result["is_ecommerce_related"] is False
    
    def test_validate_prediction_input_missing_category(self, guardrails):
        """Test prediction input validation - missing category."""
        with pytest.raises(ValidationError, match="category"):
            guardrails.validate_prediction_input({"actual_price": 100.0})
    
    def test_validate_prediction_input_empty_category(self, guardrails):
        """Test prediction input validation - empty category."""
        with pytest.raises(ValidationError, match="non-empty string"):
            guardrails.validate_prediction_input({"category": ""})
    
    def test_validate_prediction_input_non_string_category(self, guardrails):
        """Test prediction input validation - non-string category."""
        with pytest.raises(ValidationError, match="non-empty string"):
            guardrails.validate_prediction_input({"category": 123})
    
    def test_validate_prediction_input_negative_price(self, guardrails):
        """Test prediction input validation - negative price."""
        with pytest.raises(ValidationError, match="positive number"):
            guardrails.validate_prediction_input({
                "category": "Electronics",
                "actual_price": -10.0
            })
    
    def test_validate_prediction_input_zero_price(self, guardrails):
        """Test prediction input validation - zero price."""
        with pytest.raises(ValidationError, match="positive number"):
            guardrails.validate_prediction_input({
                "category": "Electronics",
                "actual_price": 0
            })
    
    def test_validate_prediction_input_invalid_rating_low(self, guardrails):
        """Test prediction input validation - rating below 0."""
        with pytest.raises(ValidationError, match="between 0 and 5"):
            guardrails.validate_prediction_input({
                "category": "Electronics",
                "rating": -1
            })
    
    def test_validate_prediction_input_invalid_rating_high(self, guardrails):
        """Test prediction input validation - rating above 5."""
        with pytest.raises(ValidationError, match="between 0 and 5"):
            guardrails.validate_prediction_input({
                "category": "Electronics",
                "rating": 6
            })
    
    def test_validate_prediction_input_valid_rating_boundaries(self, guardrails):
        """Test prediction input validation - valid rating boundaries."""
        # Rating 0 should be valid
        result = guardrails.validate_prediction_input({
            "category": "Electronics",
            "rating": 0
        })
        assert result["rating"] == 0
        
        # Rating 5 should be valid
        result = guardrails.validate_prediction_input({
            "category": "Electronics",
            "rating": 5
        })
        assert result["rating"] == 5
    
    def test_validate_prediction_input_negative_rating_count(self, guardrails):
        """Test prediction input validation - negative rating count."""
        with pytest.raises(ValidationError, match="non-negative integer"):
            guardrails.validate_prediction_input({
                "category": "Electronics",
                "rating_count": -1
            })
    
    def test_validate_prediction_input_non_integer_rating_count(self, guardrails):
        """Test prediction input validation - non-integer rating count."""
        with pytest.raises(ValidationError, match="non-negative integer"):
            guardrails.validate_prediction_input({
                "category": "Electronics",
                "rating_count": 10.5
            })
    
    def test_validate_prediction_input_valid_all_optional_fields(self, guardrails):
        """Test prediction input validation - all valid optional fields."""
        features = {
            "category": "Electronics",
            "actual_price": 100.0,
            "rating": 4.5,
            "rating_count": 100
        }
        
        result = guardrails.validate_prediction_input(features)
        assert result == features
    
    def test_validate_prediction_input_only_required(self, guardrails):
        """Test prediction input validation - only required field."""
        features = {"category": "Electronics"}
        result = guardrails.validate_prediction_input(features)
        assert result == features
    
    def test_validate_prediction_input_none_optional_fields(self, guardrails):
        """Test prediction input validation - None for optional fields."""
        features = {
            "category": "Electronics",
            "actual_price": None,
            "rating": None,
            "rating_count": None
        }
        
        result = guardrails.validate_prediction_input(features)
        assert result == features



