"""Exploratory Data Analysis script."""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.training.data_loader import load_dataset
from src.core.logging import setup_logging

logger = setup_logging()


def perform_eda(dataset_path: str, output_dir: str = "data/processed") -> None:
    """Perform exploratory data analysis on the dataset."""
    logger.info("Starting Exploratory Data Analysis...")
    
    # Load dataset
    df = load_dataset(dataset_path)
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("EXPLORATORY DATA ANALYSIS")
    print("="*80)
    
    # 1. Basic Information
    print("\n1. DATASET OVERVIEW")
    print("-" * 80)
    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    # 2. Column Information
    print("\n2. COLUMN INFORMATION")
    print("-" * 80)
    print(f"\nColumn names ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    print(f"\nData types:")
    print(df.dtypes)
    
    # 3. Missing Values
    print("\n3. MISSING VALUES")
    print("-" * 80)
    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100
    missing_df = pd.DataFrame({
        'Missing Count': missing,
        'Missing %': missing_pct
    })
    missing_df = missing_df[missing_df['Missing Count'] > 0].sort_values('Missing Count', ascending=False)
    if len(missing_df) > 0:
        print(missing_df)
    else:
        print("No missing values found!")
    
    # 4. Target Variable Analysis
    print("\n4. TARGET VARIABLE ANALYSIS (discount_percentage)")
    print("-" * 80)
    if 'discount_percentage' in df.columns:
        target = df['discount_percentage'].copy()
        
        # Clean target (remove % sign)
        if target.dtype == 'object':
            target = target.astype(str).str.replace('%', '', regex=False).str.strip()
            target = pd.to_numeric(target, errors='coerce')
        
        print(f"Data type: {target.dtype}")
        print(f"Non-null count: {target.notna().sum()} / {len(target)}")
        print(f"\nDescriptive Statistics:")
        print(target.describe())
        
        print(f"\nValue counts (top 10):")
        print(target.value_counts().head(10))
        
        # Save target distribution
        target_df = pd.DataFrame({
            'discount_percentage': target
        })
        target_df.to_csv(f"{output_dir}/target_distribution.csv", index=False)
        logger.info(f"Saved target distribution to {output_dir}/target_distribution.csv")
    
    # 5. Feature Analysis
    print("\n5. FEATURE ANALYSIS")
    print("-" * 80)
    
    # Numeric features
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if 'discount_percentage' in numeric_cols:
        numeric_cols.remove('discount_percentage')
    
    if numeric_cols:
        print(f"\nNumeric features ({len(numeric_cols)}):")
        print(df[numeric_cols].describe())
    
    # Categorical features
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    if categorical_cols:
        print(f"\nCategorical features ({len(categorical_cols)}):")
        for col in categorical_cols[:5]:  # Show first 5
            print(f"\n  {col}:")
            print(f"    Unique values: {df[col].nunique()}")
            print(f"    Top 5 values:")
            print(df[col].value_counts().head(5))
    
    # 6. Correlation Analysis (if numeric features exist)
    if len(numeric_cols) > 1:
        print("\n6. CORRELATION ANALYSIS")
        print("-" * 80)
        numeric_df = df[numeric_cols + (['discount_percentage'] if 'discount_percentage' in df.columns else [])].copy()
        
        # Clean discount_percentage if needed
        if 'discount_percentage' in numeric_df.columns and numeric_df['discount_percentage'].dtype == 'object':
            numeric_df['discount_percentage'] = numeric_df['discount_percentage'].astype(str).str.replace('%', '', regex=False).str.strip()
            numeric_df['discount_percentage'] = pd.to_numeric(numeric_df['discount_percentage'], errors='coerce')
        
        corr = numeric_df.corr()
        if 'discount_percentage' in corr.columns:
            print("\nCorrelation with target (discount_percentage):")
            target_corr = corr['discount_percentage'].drop('discount_percentage').sort_values(key=abs, ascending=False)
            print(target_corr)
            
            # Save correlation matrix
            corr.to_csv(f"{output_dir}/correlation_matrix.csv")
            logger.info(f"Saved correlation matrix to {output_dir}/correlation_matrix.csv")
    
    # 7. Data Quality Checks
    print("\n7. DATA QUALITY CHECKS")
    print("-" * 80)
    
    # Check for duplicates
    duplicates = df.duplicated().sum()
    print(f"Duplicate rows: {duplicates}")
    
    # Check for constant columns
    constant_cols = [col for col in df.columns if df[col].nunique() <= 1]
    if constant_cols:
        print(f"Constant columns (single value): {constant_cols}")
    else:
        print("No constant columns found")
    
    # 8. Summary
    print("\n8. SUMMARY")
    print("-" * 80)
    print(f"✓ Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"✓ Numeric features: {len(numeric_cols)}")
    print(f"✓ Categorical features: {len(categorical_cols)}")
    print(f"✓ Missing values: {df.isnull().sum().sum()} total")
    print(f"✓ Duplicate rows: {duplicates}")
    
    logger.info("EDA complete!")
    print("\n" + "="*80)


if __name__ == "__main__":
    dataset_path = "data/raw/amazon_sales_dataset.csv"
    
    if not Path(dataset_path).exists():
        logger.error(f"Dataset not found: {dataset_path}")
        logger.info("Please download the dataset first using scripts/download_dataset.py")
        sys.exit(1)
    
    perform_eda(dataset_path)



