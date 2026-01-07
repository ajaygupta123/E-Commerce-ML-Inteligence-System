"""Unit tests for prediction service."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

from src.services.prediction_service import PredictionService
from src.core.exceptions import ValidationError, ModelNotFoundError


@pytest.fixture
def mock_predictor():
    """Mock predictor."""
    predictor = Mock()
    predictor.model = Mock()
    predictor.model.predict.return_value = [25.5]
    predictor.feature_engineer = None
    predictor.load_model = AsyncMock()
    return predictor


@pytest.fixture
def prediction_service(mock_predictor):
    """Create prediction service with mocked predictor."""
    service = PredictionService()
    service.predictor = mock_predictor
    return service


class TestPredictionService:
    """Test prediction service."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = PredictionService()
        assert service.predictor is not None
        assert service.explainer is None
        assert service.guardrails is not None
        assert not service._model_loaded
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, prediction_service, mock_predictor):
        """Test successful model initialization."""
        await prediction_service.initialize()
        assert prediction_service._model_loaded
        assert prediction_service.explainer is not None
        mock_predictor.load_model.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test initialization failure."""
        service = PredictionService()
        service.predictor.load_model = AsyncMock(side_effect=Exception("Model not found"))
        
        with pytest.raises(ModelNotFoundError):
            await service.initialize()
    
    def test_predict_success(self, prediction_service, mock_predictor):
        """Test successful prediction."""
        # Set up mock to return actual float value
        mock_predictor.model = Mock()
        mock_predictor.model.predict.return_value = [30.0]
        prediction_service._model_loaded = True
        prediction_service.predictor = mock_predictor
        
        features = {"category": "Electronics", "actual_price": 100.0}
        result = prediction_service.predict(features)
        
        assert "predicted_discount" in result
        assert "confidence_score" in result
        assert "features" in result
        assert result["predicted_discount"] == 30.0
        assert 0 <= result["confidence_score"] <= 1
    
    def test_predict_without_model(self, prediction_service):
        """Test prediction without loaded model."""
        prediction_service._model_loaded = False
        prediction_service.predictor.model = None
        
        features = {"category": "Electronics", "actual_price": 100.0}
        
        with pytest.raises(ValueError, match="Model not loaded"):
            prediction_service.predict(features)
    
    def test_predict_with_validation_error(self, prediction_service):
        """Test prediction with invalid input."""
        prediction_service._model_loaded = True
        
        # Missing required field
        features = {"actual_price": 100.0}
        
        with pytest.raises(ValidationError):
            prediction_service.predict(features)
    
    def test_predict_confidence_calculation(self, prediction_service, mock_predictor):
        """Test confidence score calculation."""
        prediction_service._model_loaded = True
        mock_predictor.model = Mock()
        mock_predictor.model.predict.return_value = [25.0]  # Low discount
        prediction_service.predictor = mock_predictor
        
        features = {"category": "Electronics", "actual_price": 100.0}
        result = prediction_service.predict(features)
        
        # Should have high confidence for low discount
        assert result["confidence_score"] >= 0.8
    
    def test_predict_confidence_without_price(self, prediction_service, mock_predictor):
        """Test confidence reduction when price is missing."""
        prediction_service._model_loaded = True
        mock_predictor.model = Mock()
        mock_predictor.model.predict.return_value = [25.0]
        prediction_service.predictor = mock_predictor
        
        features = {"category": "Electronics"}  # No actual_price
        result = prediction_service.predict(features)
        
        # Confidence should be reduced
        assert result["confidence_score"] < 0.6  # 0.85 * 0.7 = 0.595
    
    def test_predict_with_explanation(self, prediction_service, mock_predictor):
        """Test prediction with SHAP explanation."""
        prediction_service._model_loaded = True
        prediction_service.explainer = Mock()
        prediction_service.explainer.explain.return_value = {
            "shap_values": {"category": 0.5, "actual_price": 0.3},
            "base_value": 20.0,
            "feature_importance": {"category": 0.5, "actual_price": 0.3}
        }
        mock_predictor.model = Mock()
        mock_predictor.model.predict.return_value = [25.0]
        mock_predictor.feature_engineer = None
        prediction_service.predictor = mock_predictor
        
        features = {"category": "Electronics", "actual_price": 100.0}
        result = prediction_service.predict(features, include_explanation=True)
        
        assert "explanation" in result
        assert "shap_values" in result["explanation"]
        assert "base_value" in result["explanation"]
    
    def test_predict_explanation_without_model(self, prediction_service):
        """Test explanation request without loaded model."""
        prediction_service._model_loaded = False
        prediction_service.explainer = None
        
        features = {"category": "Electronics", "actual_price": 100.0}
        
        with pytest.raises(ValueError, match="Model not loaded"):
            prediction_service.predict(features, include_explanation=True)
    
    def test_is_ready(self, prediction_service):
        """Test is_ready property."""
        prediction_service._model_loaded = False
        assert not prediction_service.is_ready
        
        prediction_service._model_loaded = True
        assert prediction_service.is_ready

