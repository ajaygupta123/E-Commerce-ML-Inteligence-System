"""Train Random Forest baseline model."""
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from pathlib import Path
import pickle

from .data_loader import load_dataset, split_features_target
from .feature_engineering import FeatureEngineer
from ...core.logging import setup_logging

logger = setup_logging()


def train_random_forest(
    dataset_path: str,
    model_output_path: str = "models/random_forest_model.pkl",
    feature_engineer_path: str = "models/feature_engineer_rf.pkl"
) -> dict:
    """
    Train Random Forest baseline model.
    
    Returns:
        Dict with model metrics and training info
    """
    logger.info("Training Random Forest model...")
    
    # Load data
    df = load_dataset(dataset_path)
    X, y = split_features_target(df)
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Feature engineering
    feature_engineer = FeatureEngineer()
    X_train_processed = feature_engineer.fit_transform(X_train)
    X_test_processed = feature_engineer.transform(X_test)
    
    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
        verbose=0,
    )
    
    model.fit(X_train_processed, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_processed)
    rmse = mean_squared_error(y_test, y_pred, squared=False)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    metrics = {
        "rmse": float(rmse),
        "mae": float(mae),
        "r2": float(r2),
    }
    
    logger.info(f"Random Forest Metrics - RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")
    
    # Save model and feature engineer
    Path(model_output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(model_output_path, 'wb') as f:
        pickle.dump(model, f)
    
    feature_engineer.save(feature_engineer_path)
    
    return {
        "model": "Random Forest",
        "metrics": metrics,
        "model_path": model_output_path,
        "feature_engineer_path": feature_engineer_path,
    }



