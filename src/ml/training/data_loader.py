"""Data loading utilities for training."""
import pandas as pd
from typing import Tuple
from pathlib import Path

from ...core.logging import setup_logging

logger = setup_logging()


def load_dataset(file_path: str) -> pd.DataFrame:
    """Load dataset from CSV file."""
    logger.info(f"Loading dataset from {file_path}")
    df = pd.read_csv(file_path)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def split_features_target(
    df: pd.DataFrame,
    target_column: str = "discount_percentage"
) -> Tuple[pd.DataFrame, pd.Series]:
    """Split dataset into features and target."""
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset")
    
    X = df.drop(columns=[target_column])
    y = df[target_column]
    
    # Convert target to numeric, handling string values (e.g., "64%" -> 64.0)
    # First, try to clean the data by removing common non-numeric characters
    if y.dtype == 'object':
        # Remove percentage signs, spaces, and other common characters
        y = y.astype(str).str.replace('%', '', regex=False)
        y = y.str.strip()
    
    # Convert to numeric, coercing errors to NaN
    y = pd.to_numeric(y, errors='coerce')
    
    # Check for any NaN values after conversion
    if y.isna().any():
        nan_count = y.isna().sum()
        logger.warning(f"Found {nan_count} NaN values in target column after conversion. Dropping these rows.")
        # Drop rows where target is NaN
        valid_mask = ~y.isna()
        X = X[valid_mask].reset_index(drop=True)
        y = y[valid_mask].reset_index(drop=True)
    
    # Ensure target is float type
    y = y.astype(float)
    
    logger.info(f"Target column dtype: {y.dtype}, shape: {y.shape}")
    
    return X, y


