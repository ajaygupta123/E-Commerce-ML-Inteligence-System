"""Test dataset for RAG evaluation."""
from typing import List, Dict, Any

# Example test cases - in production, load from JSON file
DEFAULT_TEST_CASES: List[Dict[str, Any]] = [
    {
        "question": "What are the cheapest products in the electronics category?",
        "expected_answer": "Products with lowest prices in electronics",
        "relevant_products": [],  # Would contain actual product IDs
    },
    {
        "question": "Compare products with ratings above 4.5",
        "expected_answer": "List of highly rated products",
        "relevant_products": [],
    },
    {
        "question": "What products are on sale?",
        "expected_answer": "Products with discounts",
        "relevant_products": [],
    },
]




