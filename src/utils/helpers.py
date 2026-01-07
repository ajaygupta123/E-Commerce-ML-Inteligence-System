"""Helper utility functions."""
import uuid
import re
from typing import Optional
from enum import Enum


class QuestionType(str, Enum):
    """Question type classification."""
    COMPARISON = "comparison"
    PRICE = "price"
    FEATURE = "feature"
    CATEGORY = "category"
    GENERAL = "general"


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


def classify_question_type(question: str) -> QuestionType:
    """
    Classify the type of question being asked.
    
    Args:
        question: User question string
        
    Returns:
        QuestionType enum value
    """
    question_lower = question.lower()
    
    # Comparison patterns
    comparison_patterns = [
        r"\b(compare|comparison|difference|different|better|best|vs|versus|versus|which is better|which one|prefer)\b",
        r"\b(pros? and cons?|advantages?|disadvantages?)\b"
    ]
    for pattern in comparison_patterns:
        if re.search(pattern, question_lower):
            return QuestionType.COMPARISON
    
    # Price patterns
    price_patterns = [
        r"\b(price|cost|pricing|cheap|cheapest|expensive|affordable|budget|value|worth|deal|discount|sale|offer)\b",
        r"\b(how much|what.*cost|under.*rupees?|under.*dollars?)\b"
    ]
    for pattern in price_patterns:
        if re.search(pattern, question_lower):
            return QuestionType.PRICE
    
    # Feature patterns
    feature_patterns = [
        r"\b(feature|specification|spec|support|compatible|compatibility|works with|can.*do|does.*have|has.*feature)\b",
        r"\b(what.*support|which.*support|does.*support|supports?)\b"
    ]
    for pattern in feature_patterns:
        if re.search(pattern, question_lower):
            return QuestionType.FEATURE
    
    # Category patterns
    category_patterns = [
        r"\b(category|categories|type|types|kind|kinds|available|what.*available|show.*products?|list.*products?)\b",
        r"\b(what.*products?|which.*products?|find.*products?)\b"
    ]
    for pattern in category_patterns:
        if re.search(pattern, question_lower):
            return QuestionType.CATEGORY
    
    # Default to general
    return QuestionType.GENERAL


def validate_ecommerce_query(query: str) -> bool:
    """
    Enhanced validation to check if query is e-commerce related.
    
    Uses comprehensive keyword matching including:
    - Product-related terms
    - E-commerce action verbs
    - Common product categories
    - Shopping-related terms
    """
    # Comprehensive e-commerce keywords
    ecommerce_keywords = [
        # Product terms
        "product", "products", "item", "items", "goods", "merchandise",
        # Price and value
        "price", "pricing", "cost", "discount", "discounted", "sale", "offer", "deal",
        "cheap", "cheapest", "expensive", "affordable", "budget", "value", "worth",
        # Shopping actions
        "buy", "purchase", "order", "cart", "shopping", "shop", "store",
        # Product attributes
        "brand", "category", "categories", "type", "rating", "ratings", "review", "reviews",
        "feature", "features", "specification", "specs", "specifications",
        # Comparison and selection
        "compare", "comparison", "better", "best", "recommend", "recommendation",
        "choose", "selection", "option", "options", "alternative", "alternatives",
        # Delivery and service
        "shipping", "delivery", "warranty", "return", "refund",
        # Product categories (common ones)
        "electronics", "clothing", "accessories", "home", "kitchen", "sports",
        "books", "toys", "beauty", "health", "automotive", "furniture",
        # Product types
        "cable", "cables", "headphone", "headphones", "phone", "laptop", "tablet",
        "watch", "speaker", "speakers", "charger", "chargers", "adapter", "adapters"
    ]
    
    query_lower = query.lower()
    
    # Check for e-commerce keywords
    if any(keyword in query_lower for keyword in ecommerce_keywords):
        return True
    
    # Check for product-related question patterns
    product_patterns = [
        r"\b(what|which|where|how).*(product|item|buy|purchase|available)\b",
        r"\b(show|list|find|search).*(product|item)\b",
        r"\b(product|item).*(available|in stock|for sale)\b"
    ]
    
    for pattern in product_patterns:
        if re.search(pattern, query_lower):
            return True
    
    return False


