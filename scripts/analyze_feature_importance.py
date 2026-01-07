"""Analyze feature importance using SHAP values."""
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from catboost import CatBoostRegressor
import shap
import pandas as pd
from src.ml.training.data_loader import load_dataset, split_features_target
from src.ml.training.feature_engineering import FeatureEngineer
from src.core.logging import setup_logging

logger = setup_logging()


def analyze_feature_importance(
    dataset_path: str = "data/raw/amazon_sales_dataset.csv",
    model_path: str = "models/catboost_model.cbm",
    output_path: str = "models/feature_importance.json"
):
    """Analyze and save feature importance using SHAP."""
    logger.info("Loading model and data...")
    
    # Load model
    model = CatBoostRegressor()
    model.load_model(model_path)
    
    # Load and prepare data
    df = load_dataset(dataset_path)
    X, y = split_features_target(df)
    
    # Feature engineering
    feature_engineer = FeatureEngineer()
    X_processed = feature_engineer.fit_transform(X)
    
    # Use a sample for SHAP (SHAP can be slow on large datasets)
    sample_size = min(100, len(X_processed))
    X_sample = X_processed.sample(n=sample_size, random_state=42)
    
    logger.info(f"Computing SHAP values for {sample_size} samples...")
    
    # Create SHAP explainer
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    # Calculate mean absolute SHAP values (feature importance)
    feature_importance = pd.DataFrame({
        'feature': X_processed.columns,
        'importance': abs(shap_values).mean(axis=0)
    }).sort_values('importance', ascending=False)
    
    # Get top 10 features
    top_features = feature_importance.head(10).to_dict('records')
    
    # Save results
    results = {
        'feature_importance': feature_importance.to_dict('records'),
        'top_10_features': top_features,
        'summary': {
            'total_features': len(feature_importance),
            'sample_size': sample_size,
        }
    }
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nTop 10 Most Important Features:")
    logger.info("=" * 60)
    for i, feat in enumerate(top_features, 1):
        logger.info(f"{i:2d}. {feat['feature']:30s} - Importance: {feat['importance']:.4f}")
    
    logger.info(f"\nFeature importance saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    analyze_feature_importance()
