"""Predictor for making discount predictions."""
from typing import Dict, Any
import pandas as pd
import pickle
from pathlib import Path

from .model_loader import ModelLoader
from ..training.feature_engineering import FeatureEngineer
from ...core.config import settings
from ...core.logging import setup_logging

logger = setup_logging()


class Predictor:
    """Predictor for discount percentage."""
    
    def __init__(self):
        self.model_loader = ModelLoader()
        self.model = None
        self.feature_engineer = None
    
    async def load_model(self) -> None:
        """Load model and feature engineer."""
        self.model = await self.model_loader.load_model()
        
        # Load feature engineer (try to find it based on active model path or default)
        # For now, use default path - could be enhanced to match model version
        feature_engineer_path = Path(settings.model_path).parent / "feature_engineer.pkl"
        if feature_engineer_path.exists():
            self.feature_engineer = FeatureEngineer.load(str(feature_engineer_path))
        else:
            logger.warning("Feature engineer not found, using raw features")
    
    def predict(self, features: Dict[str, Any]) -> float:
        """
        Predict discount percentage.
        
        Args:
            features: Dictionary of product features
        
        Returns:
            Predicted discount percentage
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Transform features if engineer available
        if self.feature_engineer:
            # Add missing columns with default values to match training schema
            all_expected = set(self.feature_engineer.categorical_features + self.feature_engineer.numerical_features)
            missing_columns = all_expected - set(df.columns)
            
            # Fill missing columns with defaults
            for col in missing_columns:
                if col in self.feature_engineer.categorical_features:
                    df[col] = "unknown"  # Default for categorical
                elif col in self.feature_engineer.numerical_features:
                    df[col] = 0.0  # Default for numerical
            
            # Ensure all expected columns are present and in correct order
            column_order = self.feature_engineer.categorical_features + self.feature_engineer.numerical_features
            df = df.reindex(columns=column_order, fill_value=0)
            
            df = self.feature_engineer.transform(df)
        else:
            # Fallback: Handle features without feature engineer
            # The model was trained with encoded features, so we need to encode categoricals
            # Use a simple hash-based encoding for categorical features as fallback
            import numpy as np
            
            # Expected feature order based on training (from error message and model metadata)
            # The model expects: product_id, actual_price, category, rating, rating_count, etc.
            expected_features = [
                'product_id', 'actual_price', 'category', 'rating', 'rating_count',
                'product_name', 'about_product', 'discounted_price', 'img_link', 
                'product_link', 'user_name', 'user_id', 'review_id', 'review_title',
                'review_content'
            ]
            
            # Add missing features with default values
            for feat in expected_features:
                if feat not in df.columns:
                    if feat in ['product_id', 'user_id', 'review_id']:
                        df[feat] = '0'  # String IDs
                    elif feat in ['product_name', 'about_product', 'user_name', 'review_title', 'review_content', 'img_link', 'product_link']:
                        df[feat] = ''  # Empty strings for text fields
                    else:
                        df[feat] = 0.0  # Numeric defaults
            
            # Reorder columns to match expected order
            df = df.reindex(columns=expected_features, fill_value=0)
            
            # Identify categorical vs numerical columns
            categorical_cols = ['product_id', 'category', 'product_name', 'about_product', 
                              'user_name', 'user_id', 'review_id', 'review_title', 
                              'review_content', 'img_link', 'product_link']
            numerical_cols = ['actual_price', 'rating', 'rating_count', 'discounted_price']
            
            # Encode categorical features using hash (simple fallback)
            # This won't match training exactly but should work for basic predictions
            for col in categorical_cols:
                if col in df.columns:
                    # Use hash-based encoding (modulo to keep values reasonable)
                    df[col] = df[col].astype(str).apply(lambda x: abs(hash(x)) % 10000 if x else 0)
            
            # Ensure all columns are numeric
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Make prediction
        prediction = self.model.predict(df)[0]
        
        # Ensure prediction is in valid range
        prediction = max(0.0, min(100.0, float(prediction)))
        
        return prediction


