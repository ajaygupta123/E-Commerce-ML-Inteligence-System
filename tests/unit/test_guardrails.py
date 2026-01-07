"""Tests for guardrails service."""
import pytest

from src.services.guardrails_service import GuardrailsService
from src.core.exceptions import ValidationError


def test_validate_ecommerce_query():
    """Test e-commerce query validation."""
    guardrails = GuardrailsService()
    
    # Valid e-commerce query
    result = guardrails.validate_query("What are the best products?")
    assert result["is_valid"] is True
    assert result["is_ecommerce_related"] is True
    
    # Non-e-commerce query
    result = guardrails.validate_query("What is the weather?")
    assert result["is_ecommerce_related"] is False
    
    # Invalid query (too long)
    with pytest.raises(ValidationError):
        guardrails.validate_query("x" * 1001)


def test_validate_prediction_input():
    """Test prediction input validation."""
    guardrails = GuardrailsService()
    
    # Valid input
    features = {"category": "Electronics", "actual_price": 100.0}
    result = guardrails.validate_prediction_input(features)
    assert result == features
    
    # Missing required field
    with pytest.raises(ValidationError):
        guardrails.validate_prediction_input({"actual_price": 100.0})
    
    # Invalid price
    with pytest.raises(ValidationError):
        guardrails.validate_prediction_input({"actual_price": -10, "category": "Electronics"})


