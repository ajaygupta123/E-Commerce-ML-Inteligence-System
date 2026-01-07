"""Prediction service for discount prediction."""
from typing import Dict, Any, Optional
import time

from ..ml.inference.predictor import Predictor
from ..ml.inference.explainer import Explainer
from ..core.logging import setup_logging
from ..core.exceptions import ModelNotFoundError
from .guardrails_service import GuardrailsService

logger = setup_logging()


class PredictionService:
    """Service for making discount predictions."""
    
    def __init__(self):
        self.predictor = Predictor()
        self.explainer = None  # Will be initialized after model loads
        self.guardrails = GuardrailsService()
        self._model_loaded = False
    
    async def initialize(self) -> None:
        """Initialize and load the model."""
        try:
            await self.predictor.load_model()
            # Initialize explainer after model is loaded
            self.explainer = Explainer(self.predictor.model)
            self._model_loaded = True
            logger.info("Prediction model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load prediction model: {e}")
            raise ModelNotFoundError(f"Could not load model: {e}")
    
    def predict(
        self,
        features: Dict[str, Any],
        include_explanation: bool = False
    ) -> Dict[str, Any]:
        """
        Predict discount percentage for given features.
        
        Args:
            features: Product features (price, category, rating, etc.)
            include_explanation: Whether to include SHAP explanation
        
        Returns:
            Dict with prediction, confidence, and optionally SHAP values
        """
        # Validate input
        validated_features = self.guardrails.validate_prediction_input(features)
        
        # Check if critical features are missing
        has_actual_price = validated_features.get("actual_price") is not None
        
        # Make prediction
        prediction = self.predictor.predict(validated_features)
        
        # Calculate confidence (simplified - in production use prediction intervals)
        # Lower confidence if critical features are missing
        confidence = self._calculate_confidence(prediction, has_actual_price=has_actual_price)
        
        result = {
            "predicted_discount": float(prediction),
            "confidence_score": confidence,
            "features": validated_features,
        }
        
        if include_explanation:
            if self.explainer is None and self.predictor.model is not None:
                # Initialize explainer if not already done and model is loaded
                self.explainer = Explainer(self.predictor.model)
            
            if self.explainer is None:
                raise ValueError("Model not loaded. Cannot generate explanation.")
            
            # Need to prepare features the same way predictor does
            import pandas as pd
            df = pd.DataFrame([validated_features])
            
            # Add missing columns (same logic as predictor)
            if self.predictor.feature_engineer:
                all_expected = set(
                    self.predictor.feature_engineer.categorical_features + 
                    self.predictor.feature_engineer.numerical_features
                )
                missing_columns = all_expected - set(df.columns)
                
                for col in missing_columns:
                    if col in self.predictor.feature_engineer.categorical_features:
                        df[col] = "unknown"
                    elif col in self.predictor.feature_engineer.numerical_features:
                        df[col] = 0.0
                
                column_order = (
                    self.predictor.feature_engineer.categorical_features + 
                    self.predictor.feature_engineer.numerical_features
                )
                df = df.reindex(columns=column_order, fill_value=0)
                df = self.predictor.feature_engineer.transform(df)
            
            # Use processed features for explanation
            processed_features = df.iloc[0].to_dict()
            shap_values = self.explainer.explain(processed_features, feature_names=df.columns.tolist())
            result["explanation"] = shap_values
        
        return result
    
    def _calculate_confidence(self, prediction: float, has_actual_price: bool = True) -> float:
        """
        Calculate confidence score (0-1).
        
        Simplified implementation. In production, use:
        - Prediction intervals
        - Model uncertainty quantification
        - Ensemble variance
        
        Args:
            prediction: Predicted discount percentage
            has_actual_price: Whether actual_price was provided (critical feature)
        """
        # Base confidence based on prediction range
        if 0 <= prediction <= 50:
            base_confidence = 0.85
        elif 50 < prediction <= 70:
            base_confidence = 0.75
        else:
            base_confidence = 0.65
        
        # Reduce confidence if critical features are missing
        # actual_price is the 2nd most important feature (after category)
        if not has_actual_price:
            base_confidence *= 0.7  # Reduce by 30% if missing
        
        return base_confidence
    
    @property
    def is_ready(self) -> bool:
        """Check if model is loaded and ready."""
        return self._model_loaded


