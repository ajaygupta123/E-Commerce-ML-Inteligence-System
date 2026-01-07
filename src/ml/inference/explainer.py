"""SHAP explainer for model interpretability."""
from typing import Dict, Any, List, Optional
import pandas as pd
import shap
import numpy as np

from ...core.logging import setup_logging

logger = setup_logging()


class Explainer:
    """SHAP explainer for CatBoost models."""
    
    def __init__(self, model):
        """
        Initialize SHAP explainer.
        
        Args:
            model: Trained CatBoost model
        """
        self.model = model
        self.explainer = None
    
    def explain(
        self,
        features: Dict[str, Any],
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanation for prediction.
        
        Args:
            features: Input features
            feature_names: Optional list of feature names
        
        Returns:
            Dict with SHAP values and feature importance
        """
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Create TreeExplainer for CatBoost
        if self.explainer is None:
            self.explainer = shap.TreeExplainer(self.model)
        
        # Calculate SHAP values
        shap_values = self.explainer.shap_values(df)
        
        # Get feature names
        if feature_names is None:
            feature_names = list(features.keys())
        
        # Create explanation dict
        explanation = {
            "shap_values": {
                name: float(value)
                for name, value in zip(feature_names, shap_values[0])
            },
            "base_value": float(self.explainer.expected_value),
            "feature_importance": dict(
                sorted(
                    zip(feature_names, np.abs(shap_values[0])),
                    key=lambda x: abs(x[1]),
                    reverse=True
                )
            ),
        }
        
        return explanation

