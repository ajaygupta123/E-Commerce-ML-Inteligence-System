# Model Training Summary

## Overview
This document summarizes the complete model training and evaluation process for the E-commerce Discount Prediction System.

## Dataset
- **Source**: Amazon Sales Dataset (Kaggle)
- **Size**: 1,465 rows × 16 columns
- **Target**: discount_percentage (0-100%)

## Models Trained

### 1. Random Forest (Baseline)
- **Purpose**: Simple, interpretable baseline
- **Performance**: R² = 0.003, RMSE = 19.74
- **Status**: Poor performance, not selected

### 2. LightGBM
- **Performance**: R² = 0.255, RMSE = 17.06
- **Status**: Good baseline, but outperformed

### 3. XGBoost
- **Performance**: R² = 0.024, RMSE = 19.53
- **Status**: Underperformed on this dataset

### 4. CatBoost (Selected)
- **Base Model**: R² = 0.430, RMSE = 14.92
- **Tuned Model**: R² = 0.878, RMSE = 6.89
- **Status**: **Best performing model**

## Feature Importance Analysis

Top 5 Most Important Features:
1. **category** (7.24) - Product category is the strongest predictor
2. **actual_price** (3.91) - Original price significantly impacts discount
3. **review_title** (3.64) - Text content in reviews matters
4. **about_product** (1.99) - Product description contributes
5. **discounted_price** (1.35) - Final price is relevant

**Key Finding**: Category and price features dominate, but text features (reviews, descriptions) also contribute meaningfully.

## Model Validation

### Cross-Validation (5-fold)
- **RMSE**: 9.79 ± 0.97
- **MAE**: 6.87 ± 0.51
- **R²**: 0.79 ± 0.02

**Interpretation**: Model shows consistent performance across folds with low variance, indicating good generalization.

### Holdout Validation
- **RMSE**: 8.28
- **MAE**: 6.37
- **R²**: 0.82

**Interpretation**: Model performs well on unseen data, confirming it's not overfitting.

## Hyperparameter Tuning

### Best Parameters Found
- **iterations**: 289
- **learning_rate**: 0.130
- **depth**: 5
- **l2_leaf_reg**: 4

### Performance Improvement
- **R²**: 0.43 → 0.88 (+104% improvement)
- **RMSE**: 14.92 → 6.89 (-54% reduction)
- **MAE**: 11.67 → 5.02 (-57% reduction)

**Key Insight**: Hyperparameter tuning significantly improved model performance, nearly doubling the R² score.

## Final Model Selection

**Selected Model**: CatBoost with tuned hyperparameters

**Rationale**:
1. Highest R² score (0.88)
2. Lowest RMSE (6.89)
3. Strong validation performance
4. Good generalization (low CV variance)
5. Native categorical feature handling

## Model Files

- **Base Model**: `models/catboost_model.cbm`
- **Tuned Model**: `models/tuned_catboost_model.cbm`
- **Feature Engineer**: `models/feature_engineer.pkl`
- **Comparison Results**: `models/model_comparison.json`
- **Feature Importance**: `models/feature_importance.json`
- **Validation Results**: `models/validation_results.json`
- **Tuning Results**: `models/hyperparameter_tuning_results.json`

## Recommendations

1. **Deploy Tuned Model**: Use `tuned_catboost_model.cbm` for production
2. **Feature Engineering**: Focus on category and price features
3. **Text Features**: Consider NLP techniques for review_title and about_product
4. **Monitoring**: Track model performance over time for drift detection
5. **A/B Testing**: Compare tuned vs base model in production

## Next Steps

- [x] Model training and comparison
- [x] Feature importance analysis
- [x] Cross-validation
- [x] Hyperparameter tuning
- [ ] API integration testing
- [ ] Production deployment
- [ ] Performance monitoring setup



