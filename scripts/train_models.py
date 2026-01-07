"""Script to train ML models."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.training.model_comparison import compare_models
from src.core.logging import setup_logging

logger = setup_logging()


def main():
    """Train and compare models."""
    # Update this path to your dataset
    dataset_path = "data/raw/amazon_sales_dataset.csv"
    
    if not Path(dataset_path).exists():
        logger.error(f"Dataset not found: {dataset_path}")
        logger.info("Please download the dataset first using scripts/download_dataset.py")
        return
    
    logger.info("Starting model training and comparison...")
    results = compare_models(dataset_path)
    
    logger.info("Training complete!")
    logger.info(f"Best model: {results['summary']['best_model']}")


if __name__ == "__main__":
    main()




