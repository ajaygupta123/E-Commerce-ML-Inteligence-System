# Model Card: Discount Predictor

## Model Details
- **Model Type**: CatBoostRegressor
- **Version**: 1.0.0
- **Training Date**: [To be filled after training]
- **Framework**: CatBoost 1.2.2
- **Training Time**: [To be filled]

## Intended Use
- **Primary Use**: Predict optimal discount percentage for e-commerce products
- **Users**: Marketing teams, pricing systems, recommendation engines
- **Out of Scope**: 
  - Non-e-commerce products
  - Products without price/category information
  - Seasonal trend prediction (requires time-series features)

## Training Data
- **Source**: Amazon Sales Dataset (Kaggle)
- **Size**: [To be filled after data loading]
- **Features**: 
  - price (numerical)
  - category (categorical)
  - rating (numerical, optional)
  - num_reviews (numerical, optional)
  - attributes (JSON, optional)
- **Target**: discount_percentage (0-100)
- **Train/Test Split**: 80/20
- **Preprocessing**: 
  - Label encoding for categorical features
  - Standard scaling for numerical features

## Performance Metrics

### Comparison: All Models

| Metric | Random Forest | LightGBM | XGBoost | CatBoost (Final) | Improvement (vs LightGBM) |
|--------|---------------|----------|---------|------------------|---------------------------|
| RMSE | 19.74 | 17.06 | 19.53 | 14.92 | -12.5% |
| MAE | 16.32 | 13.60 | 16.01 | 11.67 | -14.2% |
| R² | 0.003 | 0.255 | 0.024 | 0.430 | +68.7% |

### Model Selection Rationale
CatBoost was selected over LightGBM due to:
1. Better native handling of categorical features
2. Superior performance on tabular data
3. Built-in SHAP support for explainability
4. Less hyperparameter tuning required

## Feature Importance (SHAP)

Top 10 features by SHAP importance:
1. **category** - 7.24 (most important)
2. **actual_price** - 3.91
3. **review_title** - 3.64
4. **about_product** - 1.99
5. **discounted_price** - 1.35
6. **rating** - 0.98
7. **rating_count** - 0.32
8. **user_name** - 0.26
9. **product_name** - 0.11
10. **product_id** - 0.00 (not important)

**Key Insights:**
- Category is the strongest predictor of discount percentage
- Price features (actual_price, discounted_price) are highly important
- Text features (review_title, about_product) contribute significantly
- ID fields (product_id, user_id, review_id) have zero importance

## Model Architecture

- **Algorithm**: Gradient Boosting Decision Trees
- **Base Model Hyperparameters**:
  - iterations: 100
  - learning_rate: 0.1
  - depth: 7
  - loss_function: RMSE
  - early_stopping_rounds: 10

- **Tuned Model Hyperparameters** (Best Performance):
  - iterations: 289
  - learning_rate: 0.130
  - depth: 5
  - l2_leaf_reg: 4
  - loss_function: RMSE

## Model Validation

### Cross-Validation Results (5-fold)
- **RMSE**: 9.79 ± 0.97
- **MAE**: 6.87 ± 0.51
- **R²**: 0.79 ± 0.02

### Holdout Validation (80/20 split)
- **RMSE**: 8.28
- **MAE**: 6.37
- **R²**: 0.82

### Tuned Model Performance
- **RMSE**: 6.89 (improved from 14.92)
- **MAE**: 5.02 (improved from 11.67)
- **R²**: 0.88 (improved from 0.43)
- **Improvement**: 104% increase in R² score

## Limitations

1. **Data Dependency**: 
   - Trained on Amazon data; may not generalize to other platforms
   - Performance depends on data quality

2. **Temporal Limitations**:
   - Does not account for seasonal trends
   - No time-series features

3. **Feature Limitations**:
   - Requires at least price and category
   - Optional features improve accuracy but not required

4. **Prediction Range**:
   - Predictions clamped to 0-100%
   - May not capture extreme discount scenarios

5. **Cold Start**:
   - New products with no historical data may have lower accuracy

## Ethical Considerations

- **Bias**: Model may reflect biases in training data
- **Fairness**: Discount predictions should be reviewed for fairness
- **Transparency**: SHAP explanations provided for all predictions
- **Privacy**: No PII in training data
- **Human Oversight**: Predictions should be reviewed by humans before implementation

## Monitoring

- **Prediction Logging**: All predictions logged to database
- **Performance Tracking**: Metrics tracked over time
- **Drift Detection**: [To be implemented] Monitor for data drift
- **A/B Testing**: [To be implemented] Support for model versioning

## Deployment

- **Model Format**: CatBoost .cbm file
- **Size**: [To be filled]
- **Inference Latency**: [To be measured]
- **Throughput**: [To be measured]

## Maintenance

- **Retraining Schedule**: [To be determined]
- **Version Control**: Model versions tracked in metadata
- **Rollback**: Support for rolling back to previous versions

## Contact

For questions or issues, please refer to the project repository.


