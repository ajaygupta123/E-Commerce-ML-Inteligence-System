"""Compare multiple ML models."""
from typing import Dict, List
import json
from pathlib import Path

from .train_lightgbm import train_lightgbm
from .train_catboost import train_catboost
from .train_xgboost import train_xgboost
from .train_random_forest import train_random_forest
from ...core.logging import setup_logging

logger = setup_logging()


def compare_models(
    dataset_path: str,
    output_path: str = "models/model_comparison.json"
) -> Dict:
    """
    Train multiple models and generate comparison report.
    
    Returns:
        Dict with comparison metrics for all models
    """
    logger.info("Starting model comparison...")
    
    results = {}
    
    # Train Random Forest (baseline)
    try:
        logger.info("\n" + "="*60)
        logger.info("Training Random Forest (Baseline)")
        logger.info("="*60)
        results["random_forest"] = train_random_forest(dataset_path)
    except Exception as e:
        logger.error(f"Random Forest training failed: {e}")
        results["random_forest"] = {"error": str(e)}
    
    # Train LightGBM
    try:
        logger.info("\n" + "="*60)
        logger.info("Training LightGBM")
        logger.info("="*60)
        results["lightgbm"] = train_lightgbm(dataset_path)
    except Exception as e:
        logger.error(f"LightGBM training failed: {e}")
        results["lightgbm"] = {"error": str(e)}
    
    # Train XGBoost
    try:
        logger.info("\n" + "="*60)
        logger.info("Training XGBoost")
        logger.info("="*60)
        results["xgboost"] = train_xgboost(dataset_path)
    except Exception as e:
        logger.error(f"XGBoost training failed: {e}")
        results["xgboost"] = {"error": str(e)}
    
    # Train CatBoost
    try:
        logger.info("\n" + "="*60)
        logger.info("Training CatBoost")
        logger.info("="*60)
        results["catboost"] = train_catboost(dataset_path)
    except Exception as e:
        logger.error(f"CatBoost training failed: {e}")
        results["catboost"] = {"error": str(e)}
    
    # Calculate best model
    valid_results = {
        name: res for name, res in results.items()
        if "metrics" in res and "r2" in res["metrics"]
    }
    
    if valid_results:
        best_model_name = max(
            valid_results.keys(),
            key=lambda x: valid_results[x]["metrics"]["r2"]
        )
        best_model = valid_results[best_model_name]
        
        # Create comparison table
        comparison_table = []
        for name, res in valid_results.items():
            metrics = res["metrics"]
            comparison_table.append({
                "model": name,
                "rmse": metrics["rmse"],
                "mae": metrics["mae"],
                "r2": metrics["r2"],
            })
        
        # Sort by R² (descending)
        comparison_table.sort(key=lambda x: x["r2"], reverse=True)
        
        comparison = {
            "models": results,
            "comparison_table": comparison_table,
            "summary": {
                "best_model": best_model_name,
                "best_metrics": best_model["metrics"],
                "total_models_trained": len(valid_results),
            },
        }
    else:
        comparison = {
            "models": results,
            "error": "No models trained successfully",
        }
    
    # Save comparison
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    logger.info("\n" + "="*60)
    logger.info("MODEL COMPARISON SUMMARY")
    logger.info("="*60)
    
    if valid_results:
        logger.info("\nModel Performance (sorted by R²):")
        for i, entry in enumerate(comparison_table, 1):
            logger.info(
                f"{i}. {entry['model'].upper():15s} - "
                f"RMSE: {entry['rmse']:.4f}, "
                f"MAE: {entry['mae']:.4f}, "
                f"R²: {entry['r2']:.4f}"
            )
        
        logger.info(f"\n✓ Best Model: {best_model_name.upper()}")
        logger.info(f"  R² Score: {best_model['metrics']['r2']:.4f}")
    
    logger.info("\nModel comparison complete!")
    logger.info(f"Results saved to: {output_path}")
    
    return comparison


