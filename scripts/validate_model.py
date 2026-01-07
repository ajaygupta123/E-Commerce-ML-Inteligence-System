"""Validate model with cross-validation and holdout set."""
import sys
from pathlib import Path
import json
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from catboost import CatBoostRegressor
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from src.ml.training.data_loader import load_dataset, split_features_target
from src.ml.training.feature_engineering import FeatureEngineer
from src.core.logging import setup_logging

logger = setup_logging()


def validate_model(
    dataset_path: str = "data/raw/amazon_sales_dataset.csv",
    output_path: str = "models/validation_results.json"
):
    """Perform cross-validation and holdout validation."""
    logger.info("Starting model validation...")
    
    # Load and prepare data
    df = load_dataset(dataset_path)
    X, y = split_features_target(df)
    
    # Feature engineering
    feature_engineer = FeatureEngineer()
    X_processed = feature_engineer.fit_transform(X)
    
    logger.info(f"Dataset shape: {X_processed.shape}")
    logger.info(f"Target distribution: mean={y.mean():.2f}, std={y.std():.2f}")
    
    # Cross-validation
    logger.info("\nPerforming 5-fold cross-validation...")
    model = CatBoostRegressor(
        iterations=100,
        learning_rate=0.1,
        depth=7,
        loss_function='RMSE',
        random_seed=42,
        verbose=False,
    )
    
    kfold = KFold(n_splits=5, shuffle=True, random_state=42)
    
    cv_scores_rmse = -cross_val_score(
        model, X_processed, y, cv=kfold, 
        scoring='neg_root_mean_squared_error', n_jobs=-1
    )
    cv_scores_r2 = cross_val_score(
        model, X_processed, y, cv=kfold, 
        scoring='r2', n_jobs=-1
    )
    cv_scores_mae = -cross_val_score(
        model, X_processed, y, cv=kfold, 
        scoring='neg_mean_absolute_error', n_jobs=-1
    )
    
    cv_results = {
        'rmse': {
            'mean': float(cv_scores_rmse.mean()),
            'std': float(cv_scores_rmse.std()),
            'scores': cv_scores_rmse.tolist(),
        },
        'mae': {
            'mean': float(cv_scores_mae.mean()),
            'std': float(cv_scores_mae.std()),
            'scores': cv_scores_mae.tolist(),
        },
        'r2': {
            'mean': float(cv_scores_r2.mean()),
            'std': float(cv_scores_r2.std()),
            'scores': cv_scores_r2.tolist(),
        },
    }
    
    logger.info(f"\nCross-Validation Results (5-fold):")
    logger.info(f"  RMSE: {cv_results['rmse']['mean']:.4f} ± {cv_results['rmse']['std']:.4f}")
    logger.info(f"  MAE:  {cv_results['mae']['mean']:.4f} ± {cv_results['mae']['std']:.4f}")
    logger.info(f"  R²:   {cv_results['r2']['mean']:.4f} ± {cv_results['r2']['std']:.4f}")
    
    # Holdout validation (train on 80%, test on 20%)
    logger.info("\nPerforming holdout validation (80/20 split)...")
    from sklearn.model_selection import train_test_split
    
    X_train, X_test, y_train, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42
    )
    
    model.fit(X_train, y_train, verbose=False)
    y_pred = model.predict(X_test)
    
    holdout_results = {
        'rmse': float(mean_squared_error(y_test, y_pred, squared=False)),
        'mae': float(mean_absolute_error(y_test, y_pred)),
        'r2': float(r2_score(y_test, y_pred)),
        'test_size': len(y_test),
        'train_size': len(y_train),
    }
    
    logger.info(f"\nHoldout Validation Results:")
    logger.info(f"  RMSE: {holdout_results['rmse']:.4f}")
    logger.info(f"  MAE:  {holdout_results['mae']:.4f}")
    logger.info(f"  R²:   {holdout_results['r2']:.4f}")
    
    # Save results
    results = {
        'cross_validation': cv_results,
        'holdout_validation': holdout_results,
        'summary': {
            'cv_rmse_mean': cv_results['rmse']['mean'],
            'cv_r2_mean': cv_results['r2']['mean'],
            'holdout_rmse': holdout_results['rmse'],
            'holdout_r2': holdout_results['r2'],
        }
    }
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nValidation results saved to: {output_path}")
    
    return results


if __name__ == "__main__":
    validate_model()



