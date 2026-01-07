"""Integration tests for RAG flow."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock

from src.api.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


@pytest.fixture
def mock_rag_service():
    """Mock RAG service."""
    service = Mock()
    service.answer_question = AsyncMock(return_value={
        "answer": "Here are the best products...",
        "retrieved_products": [
            {"id": "1", "name": "Product 1"},
            {"id": "2", "name": "Product 2"}
        ],
        "metadata": {
            "retrieval_scores": [0.9, 0.8],
            "question_type": "GENERAL",
            "latency_ms": 1500,
            "cached": False
        }
    })
    return service


class TestRAGFlow:
    """Test full RAG flow."""
    
    def test_answer_question_success(self, client, mock_rag_service):
        """Test successful question answering."""
        with patch('src.api.dependencies.get_rag_service', return_value=mock_rag_service):
            response = client.post(
                "/v1/answer_question",
                json={
                    "question": "What are the best products?",
                    "top_k": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "retrieved_products" in data
            assert "metadata" in data
            assert len(data["retrieved_products"]) == 2
    
    def test_answer_question_missing_question(self, client):
        """Test question answering with missing question."""
        response = client.post(
            "/v1/answer_question",
            json={
                "top_k": 5
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_answer_question_empty_question(self, client):
        """Test question answering with empty question."""
        response = client.post(
            "/v1/answer_question",
            json={
                "question": "",
                "top_k": 5
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_answer_question_invalid_top_k(self, client):
        """Test question answering with invalid top_k."""
        response = client.post(
            "/v1/answer_question",
            json={
                "question": "What are the best products?",
                "top_k": 0  # Invalid
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_answer_question_too_large_top_k(self, client):
        """Test question answering with top_k exceeding max."""
        response = client.post(
            "/v1/answer_question",
            json={
                "question": "What are the best products?",
                "top_k": 25  # Exceeds max (20)
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_answer_question_non_ecommerce_query(self, client, mock_rag_service):
        """Test question answering with non-e-commerce query."""
        mock_rag_service.answer_question = AsyncMock(side_effect=ValueError("Query not e-commerce related"))
        
        with patch('src.api.dependencies.get_rag_service', return_value=mock_rag_service):
            response = client.post(
                "/v1/answer_question",
                json={
                    "question": "What is the weather?",
                    "top_k": 5
                }
            )
            
            assert response.status_code == 400
    
    def test_answer_question_cached_response(self, client, mock_rag_service):
        """Test cached question response."""
        mock_rag_service.answer_question = AsyncMock(return_value={
            "answer": "Cached answer",
            "retrieved_products": [],
            "metadata": {
                "latency_ms": 10,
                "cached": True
            }
        })
        
        with patch('src.api.dependencies.get_rag_service', return_value=mock_rag_service):
            response = client.post(
                "/v1/answer_question",
                json={
                    "question": "What are the best products?",
                    "top_k": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["metadata"]["cached"] is True
            assert data["metadata"]["latency_ms"] < 100  # Should be fast



