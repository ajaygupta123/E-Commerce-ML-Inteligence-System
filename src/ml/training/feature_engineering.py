"""Feature engineering for ML models."""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sklearn.preprocessing import LabelEncoder, StandardScaler
import pickle

from ...core.logging import setup_logging

logger = setup_logging()


class FeatureEngineer:
    """Feature engineering pipeline."""
    
    def __init__(self):
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.scaler = StandardScaler()
        self.categorical_features: List[str] = []
        self.numerical_features: List[str] = []
        self._fitted = False
    
    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Fit transformers and transform features."""
        X_processed = X.copy()
        
        # Identify feature types
        self.categorical_features = X_processed.select_dtypes(
            include=['object', 'category']
        ).columns.tolist()
        
        self.numerical_features = X_processed.select_dtypes(
            include=[np.number]
        ).columns.tolist()
        
        # Encode categorical features
        for col in self.categorical_features:
            le = LabelEncoder()
            X_processed[col] = le.fit_transform(X_processed[col].astype(str))
            self.label_encoders[col] = le
        
        # Scale numerical features
        if self.numerical_features:
            X_processed[self.numerical_features] = self.scaler.fit_transform(
                X_processed[self.numerical_features]
            )
        
        self._fitted = True
        logger.info(f"Processed {len(self.categorical_features)} categorical and {len(self.numerical_features)} numerical features")
        
        return X_processed
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform features using fitted transformers."""
        if not self._fitted:
            raise ValueError("Feature engineer must be fitted first")
        
        X_processed = X.copy()
        
        # Encode categorical features
        for col in self.categorical_features:
            if col in self.label_encoders:
                le = self.label_encoders[col]
                # Handle unseen categories
                X_processed[col] = X_processed[col].astype(str).apply(
                    lambda x: le.transform([x])[0] if x in le.classes_ else -1
                )
        
        # Scale numerical features
        if self.numerical_features:
            X_processed[self.numerical_features] = self.scaler.transform(
                X_processed[self.numerical_features]
            )
        
        return X_processed
    
    def transform_dict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a dictionary of features."""
        df = pd.DataFrame([features])
        df_transformed = self.transform(df)
        return df_transformed.iloc[0].to_dict()
    
    def save(self, file_path: str) -> None:
        """Save feature engineer to file."""
        with open(file_path, 'wb') as f:
            pickle.dump({
                'label_encoders': self.label_encoders,
                'scaler': self.scaler,
                'categorical_features': self.categorical_features,
                'numerical_features': self.numerical_features,
                '_fitted': self._fitted,
            }, f)
    
    @classmethod
    def load(cls, file_path: str) -> 'FeatureEngineer':
        """Load feature engineer from file."""
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        engineer = cls()
        engineer.label_encoders = data['label_encoders']
        engineer.scaler = data['scaler']
        engineer.categorical_features = data['categorical_features']
        engineer.numerical_features = data['numerical_features']
        engineer._fitted = data['_fitted']
        
        return engineer




