"""Guardrails service for input validation and safety checks."""
from typing import Dict, Any
import re

from ..utils.helpers import validate_ecommerce_query
from ..core.exceptions import ValidationError
from ..core.logging import setup_logging

logger = setup_logging()


class GuardrailsService:
    """Service for input validation and safety checks."""
    
    # Harmful content patterns (basic - production would use ML classifier)
    HARMFUL_PATTERNS = [
        r"\b(hack|exploit|attack|malware|virus)\b",
        r"\b(kill|murder|violence|weapon)\b",
        r"\b(drug|illegal|stolen)\b",
    ]
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate and check query for safety.
        
        Returns:
            Dict with 'is_valid', 'is_ecommerce_related', 'is_safe', 'reason'
        """
        if not query or not isinstance(query, str):
            raise ValidationError("Query must be a non-empty string")
        
        if len(query) > 1000:
            raise ValidationError("Query too long (max 1000 characters)")
        
        # Check if e-commerce related
        is_ecommerce_related = validate_ecommerce_query(query)
        
        # Check for harmful content
        is_safe = self._check_harmful_content(query)
        
        result = {
            "is_valid": True,
            "is_ecommerce_related": is_ecommerce_related,
            "is_safe": is_safe,
            "reason": None,
        }
        
        if not is_safe:
            result["is_valid"] = False
            result["reason"] = "Query contains potentially harmful content"
        
        return result
    
    def _check_harmful_content(self, text: str) -> bool:
        """Check if text contains harmful patterns."""
        text_lower = text.lower()
        for pattern in self.HARMFUL_PATTERNS:
            if re.search(pattern, text_lower):
                return False
        return True
    
    def validate_prediction_input(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Validate features for prediction.
        
        Validates fields matching the training dataset:
        - actual_price (optional but recommended): Product price
        - category (required): Product category
        - rating (optional): Product rating 0-5
        - rating_count (optional): Number of reviews
        """
        # Only category is required
        if "category" not in features:
            raise ValidationError("Missing required field: category")
        
        if not isinstance(features["category"], str) or not features["category"]:
            raise ValidationError("Category must be a non-empty string")
        
        # Validate actual_price if provided
        if "actual_price" in features and features["actual_price"] is not None:
            if not isinstance(features["actual_price"], (int, float)) or features["actual_price"] <= 0:
                raise ValidationError("actual_price must be a positive number")
        
        # Validate optional fields if provided
        if "rating" in features and features["rating"] is not None:
            rating = features["rating"]
            if not isinstance(rating, (int, float)) or rating < 0 or rating > 5:
                raise ValidationError("Rating must be a number between 0 and 5")
        
        if "rating_count" in features and features["rating_count"] is not None:
            rating_count = features["rating_count"]
            if not isinstance(rating_count, int) or rating_count < 0:
                raise ValidationError("rating_count must be a non-negative integer")
        
        return features


