"""Test model locally without Docker/API."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from catboost import CatBoostRegressor
from src.ml.training.feature_engineering import FeatureEngineer
from src.ml.inference.explainer import Explainer
from src.core.logging import setup_logging

logger = setup_logging()


def test_model_locally():
    """Test the trained model locally."""
    logger.info("Testing CatBoost model locally...")
    
    # Load model
    model_path = "models/tuned_catboost_model.cbm"
    if not Path(model_path).exists():
        logger.warning(f"Tuned model not found: {model_path}")
        logger.info("Trying base model...")
        model_path = "models/catboost_model.cbm"
    
    if not Path(model_path).exists():
        logger.error("No model found! Please train models first.")
        return
    
    logger.info(f"Loading model from: {model_path}")
    model = CatBoostRegressor()
    model.load_model(model_path)
    
    # Load feature engineer
    feature_engineer_path = "models/feature_engineer.pkl"
    if Path(feature_engineer_path).exists():
        feature_engineer = FeatureEngineer.load(feature_engineer_path)
    else:
        logger.warning("Feature engineer not found, using raw features")
        feature_engineer = None
    
    # Test cases
    test_cases = [
        {
            "name": "Electronics - High Price",
            "features": {
                "price": 299.99,
                "category": "Electronics",
                "rating": 4.5,
                "num_reviews": 1000,
            }
        },
        {
            "name": "Clothing - Medium Price",
            "features": {
                "price": 49.99,
                "category": "Clothing",
                "rating": 4.0,
            }
        },
        {
            "name": "Home & Kitchen - Low Price",
            "features": {
                "price": 19.99,
                "category": "Home & Kitchen",
            }
        },
    ]
    
    logger.info("\n" + "="*60)
    logger.info("MODEL PREDICTION TESTS")
    logger.info("="*60)
    
    for test_case in test_cases:
        logger.info(f"\nTest: {test_case['name']}")
        logger.info(f"Features: {test_case['features']}")
        
        try:
            # Prepare features
            import pandas as pd
            df = pd.DataFrame([test_case['features']])
            
            if feature_engineer:
                df = feature_engineer.transform(df)
            
            # Predict
            prediction = model.predict(df)[0]
            prediction = max(0.0, min(100.0, float(prediction)))
            
            logger.info(f"  → Predicted Discount: {prediction:.2f}%")
            
            # Get SHAP explanation if possible
            try:
                explainer = Explainer(model)
                explanation = explainer.explain(
                    test_case['features'],
                    feature_names=list(test_case['features'].keys())
                )
                
                logger.info(f"  → Top contributing features:")
                top_features = sorted(
                    explanation['feature_importance'].items(),
                    key=lambda x: abs(x[1]),
                    reverse=True
                )[:3]
                
                for feat, importance in top_features:
                    logger.info(f"      • {feat}: {importance:+.2f}")
            except Exception as e:
                logger.debug(f"  → Explanation unavailable: {e}")
                
        except Exception as e:
            logger.error(f"  ✗ Prediction failed: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("Model test complete!")
    logger.info("="*60)


if __name__ == "__main__":
    test_model_locally()



