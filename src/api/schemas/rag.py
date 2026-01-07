"""RAG API schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class QuestionRequest(BaseModel):
    """Request for RAG question answering."""
    question: str = Field(..., min_length=1, max_length=1000, description="User question")
    top_k: int = Field(5, ge=1, le=20, description="Number of products to retrieve")


class QuestionResponse(BaseModel):
    """Response with RAG answer."""
    answer: str = Field(..., description="Generated answer")
    retrieved_products: List[Dict[str, Any]] = Field(..., description="Retrieved products")
    metadata: Dict[str, Any] = Field(..., description="Retrieval and generation metadata")


class EvaluationRequest(BaseModel):
    """Request for RAG evaluation."""
    test_cases: List[Dict[str, Any]] = Field(..., description="Test cases for evaluation")


class EvaluationResponse(BaseModel):
    """Response with RAG evaluation metrics."""
    retrieval_metrics: Dict[str, float] = Field(..., description="Retrieval metrics")
    generation_metrics: Dict[str, float] = Field(..., description="Generation metrics")
    num_test_cases: int = Field(..., description="Number of test cases evaluated")




