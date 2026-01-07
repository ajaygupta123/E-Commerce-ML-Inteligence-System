"""Hyperparameter tuning for CatBoost model."""
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import randint, uniform
from src.ml.training.data_loader import load_dataset, split_features_target
from src.ml.training.feature_engineering import FeatureEngineer
from src.core.logging import setup_logging

logger = setup_logging()


def tune_hyperparameters(
    dataset_path: str = "data/raw/amazon_sales_dataset.csv",
    output_path: str = "models/tuned_catboost_model.cbm",
    results_path: str = "models/hyperparameter_tuning_results.json"
):
    """Perform hyperparameter tuning using RandomizedSearchCV."""
    logger.info("Starting hyperparameter tuning...")
    
    # Load and prepare data
    df = load_dataset(dataset_path)
    X, y = split_features_target(df)
    
    # Feature engineering
    feature_engineer = FeatureEngineer()
    X_processed = feature_engineer.fit_transform(X)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42
    )
    
    # Define parameter grid
    param_distributions = {
        'iterations': randint(100, 300),
        'learning_rate': uniform(0.01, 0.2),
        'depth': randint(4, 10),
        'l2_leaf_reg': randint(1, 10),
    }
    
    logger.info("Parameter grid:")
    for param, dist in param_distributions.items():
        logger.info(f"  {param}: {dist}")
    
    # Base model
    base_model = CatBoostRegressor(
        loss_function='RMSE',
        random_seed=42,
        verbose=False,
    )
    
    # Randomized search
    logger.info("\nPerforming randomized search (20 iterations)...")
    random_search = RandomizedSearchCV(
        base_model,
        param_distributions,
        n_iter=20,
        cv=3,
        scoring='neg_root_mean_squared_error',
        n_jobs=-1,
        random_state=42,
        verbose=1,
    )
    
    random_search.fit(X_train, y_train)
    
    # Get best model
    best_model = random_search.best_estimator_
    best_params = random_search.best_params_
    best_score = -random_search.best_score_
    
    logger.info(f"\nBest parameters found:")
    for param, value in best_params.items():
        logger.info(f"  {param}: {value}")
    logger.info(f"Best CV RMSE: {best_score:.4f}")
    
    # Evaluate on test set
    y_pred = best_model.predict(X_test)
    test_rmse = mean_squared_error(y_test, y_pred, squared=False)
    test_mae = mean_absolute_error(y_test, y_pred)
    test_r2 = r2_score(y_test, y_pred)
    
    logger.info(f"\nTest set performance with best model:")
    logger.info(f"  RMSE: {test_rmse:.4f}")
    logger.info(f"  MAE:  {test_mae:.4f}")
    logger.info(f"  R²:   {test_r2:.4f}")
    
    # Save tuned model
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    best_model.save_model(output_path)
    logger.info(f"\nTuned model saved to: {output_path}")
    
    # Save results
    results = {
        'best_parameters': best_params,
        'cv_performance': {
            'best_rmse': float(best_score),
        },
        'test_performance': {
            'rmse': float(test_rmse),
            'mae': float(test_mae),
            'r2': float(test_r2),
        },
        'all_results': [
            {
                'params': dict(params),
                'score': float(-score),
            }
            for params, score in zip(
                random_search.cv_results_['params'],
                random_search.cv_results_['mean_test_score']
            )
        ],
    }
    
    Path(results_path).parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Tuning results saved to: {results_path}")
    
    return best_model, results


if __name__ == "__main__":
    tune_hyperparameters()



