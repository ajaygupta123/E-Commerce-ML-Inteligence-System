"""Script to download Amazon Sales Dataset."""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Download dataset from Kaggle."""
    dataset_path = Path("data/raw/amazon_sales_dataset.csv")
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("To download the Amazon Sales Dataset:")
    print("1. Install kaggle: pip install kaggle")
    print("2. Set up Kaggle API credentials: https://www.kaggle.com/docs/api")
    print("3. Run: kaggle datasets download -d karkavelrajaj/amazon-sales-dataset")
    print("4. Extract to data/raw/")
    print("\nOr manually download from:")
    print("https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset")


if __name__ == "__main__":
    main()

