"""Unit tests for embedding service."""
import pytest
from unittest.mock import Mock, patch
import numpy as np

from src.services.embedding_service import EmbeddingService, _embedding_model


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer."""
    mock_model = Mock()
    mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4]])
    return mock_model


class TestEmbeddingService:
    """Test embedding service."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = EmbeddingService()
        assert service.model_name is not None
        assert service._model is None
    
    def test_initialization_with_custom_model(self):
        """Test initialization with custom model name."""
        service = EmbeddingService(model_name="custom-model")
        assert service.model_name == "custom-model"
    
    @patch('src.services.embedding_service._embedding_model', None)
    @patch('src.services.embedding_service.SentenceTransformer')
    def test_model_lazy_loading(self, mock_st, mock_sentence_transformer):
        """Test that model is loaded lazily."""
        mock_st.return_value = mock_sentence_transformer
        
        service = EmbeddingService()
        # Model should not be loaded yet
        assert service._model is None
        
        # Accessing model property should trigger loading
        model = service.model
        mock_st.assert_called_once()
        assert model == mock_sentence_transformer
    
    @patch('src.services.embedding_service._embedding_model', None)
    @patch('src.services.embedding_service.SentenceTransformer')
    def test_encode_single_text(self, mock_st, mock_sentence_transformer):
        """Test encoding a single text."""
        mock_st.return_value = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        
        service = EmbeddingService()
        result = service.encode_single("test text")
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert result == [0.1, 0.2, 0.3]
        mock_sentence_transformer.encode.assert_called_once()
    
    @patch('src.services.embedding_service._embedding_model', None)
    @patch('src.services.embedding_service.SentenceTransformer')
    def test_encode_multiple_texts(self, mock_st, mock_sentence_transformer):
        """Test encoding multiple texts."""
        mock_st.return_value = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ])
        
        service = EmbeddingService()
        texts = ["text1", "text2"]
        result = service.encode(texts)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 3)
        mock_sentence_transformer.encode.assert_called_once_with(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
    
    @patch('src.services.embedding_service._embedding_model', None)
    @patch('src.services.embedding_service.SentenceTransformer')
    def test_encode_string_conversion(self, mock_st, mock_sentence_transformer):
        """Test that single string is converted to list."""
        mock_st.return_value = mock_sentence_transformer
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2]])
        
        service = EmbeddingService()
        result = service.encode("single text")
        
        # Should convert string to list internally
        mock_sentence_transformer.encode.assert_called_once()
        call_args = mock_sentence_transformer.encode.call_args[0][0]
        assert isinstance(call_args, list)
        assert len(call_args) == 1
    
    @patch('src.services.embedding_service._embedding_model', None)
    @patch('src.services.embedding_service.SentenceTransformer')
    def test_encode_normalization(self, mock_st, mock_sentence_transformer):
        """Test that embeddings are normalized."""
        mock_st.return_value = mock_sentence_transformer
        
        service = EmbeddingService()
        service.encode(["test"])
        
        # Check that normalize_embeddings=True is passed
        call_kwargs = mock_sentence_transformer.encode.call_args[1]
        assert call_kwargs["normalize_embeddings"] is True
        assert call_kwargs["convert_to_numpy"] is True



