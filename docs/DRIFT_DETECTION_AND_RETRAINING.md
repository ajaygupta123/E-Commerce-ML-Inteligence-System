# Drift Detection and Automated Retraining

## Overview

The Drift Detection and Automated Retraining system monitors ML model performance and data distributions to detect when models degrade over time. When drift is detected, the system can trigger model retraining and deploy new versions, ensuring models remain accurate as data patterns change.

## Key Features

- **Data Drift Detection**: Monitors feature distribution changes using statistical tests
- **Performance Drift Detection**: Tracks prediction accuracy degradation (requires ground truth)
- **Automated Scheduling**: Monthly drift detection runs automatically
- **Manual Retraining**: On-demand model retraining with versioning
- **Model Versioning**: Track and deploy specific model versions
- **Zero Latency Impact**: All detection runs in background, no API request delays

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Prediction API                            │
│  (Logs all predictions to prediction_logs table)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Monthly Scheduler (APScheduler)                  │
│  Runs drift detection on 1st of each month at 2 AM          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Drift Detection Service                            │
│  • Compares recent vs historical predictions                 │
│  • Calculates data drift scores                              │
│  • Calculates performance drift (if ground truth available)  │
│  • Stores results in drift_logs table                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Alert/Notification                              │
│  Logs drift detection results                               │
│  (Can be extended with webhooks/email)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (Manual Approval)
┌─────────────────────────────────────────────────────────────┐
│            Retraining Service                                │
│  • Triggers model training                                   │
│  • Saves new model with version                             │
│  • Validates model performance                              │
│  • Stores in model_versions table                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (Manual Deployment)
┌─────────────────────────────────────────────────────────────┐
│            Model Versioning                                  │
│  • Tracks all model versions                                │
│  • Hot-swaps active model                                   │
│  • Supports rollback                                        │
└─────────────────────────────────────────────────────────────┘
```

## Drift Detection

### Data Drift

Data drift occurs when the distribution of input features changes over time, making the model less accurate on new data.

**Detection Method**:
- **Numerical Features**: Kolmogorov-Smirnov (KS) test compares distributions
- **Categorical Features**: Chi-square test or total variation distance
- **Comparison Windows**: 
  - Reference period: Last 30 days (configurable)
  - Current period: Last 7 days (configurable)

**Drift Score Calculation**:
```python
# For each feature:
drift_score = statistical_test(reference_distribution, current_distribution)

# Overall drift score = max(drift_score across all features)
drift_detected = overall_drift_score > threshold (default: 0.3)
```

**Example**:
- Reference period: Mean price = $50, std = $10
- Current period: Mean price = $70, std = $15
- KS statistic = 0.45 → Drift detected (threshold: 0.3)

### Performance Drift

Performance drift occurs when model accuracy degrades over time, even if input distributions remain stable.

**Detection Method**:
- Requires ground truth data (`actual_discount` in `prediction_logs`)
- Compares Mean Absolute Error (MAE) between periods
- Flags drift if performance degrades beyond threshold (default: 10%)

**Metrics Calculated**:
- MAE (Mean Absolute Error)
- MSE (Mean Squared Error)
- RMSE (Root Mean Squared Error)

**Drift Score Calculation**:
```python
baseline_mae = 5.0  # Expected baseline performance
current_mae = calculate_mae(recent_predictions_with_ground_truth)
performance_drift_score = (current_mae - baseline_mae) / baseline_mae
drift_detected = performance_drift_score > threshold (default: 0.1)
```

## Database Schema

### Table: `drift_logs`

Tracks drift detection history.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `detection_date` | DateTime | When drift detection ran |
| `data_drift_score` | Float | Overall data drift score (0-1) |
| `performance_drift_score` | Float | Performance drift score (nullable) |
| `drift_detected` | Boolean | Whether drift was detected |
| `recommendation` | String(50) | "retrain", "monitor", or "no_action" |
| `drift_metadata` | JSON | Detailed metrics per feature |
| `created_at` | DateTime | Timestamp |

**Indexes**:
- `ix_drift_logs_detection_date` - For time-based queries

### Table: `model_versions`

Tracks all trained model versions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `version` | String(100) | Version identifier (e.g., "v20260107-143000") |
| `model_path` | String(500) | Path to model file |
| `trained_at` | DateTime | When model was trained |
| `training_metrics` | JSON | MAE, MSE, R², etc. |
| `is_active` | Boolean | Currently deployed model |
| `drift_triggered` | Boolean | Retrained due to drift detection |
| `created_at` | DateTime | Timestamp |

**Indexes**:
- `ix_model_versions_version` - For version lookup
- `ix_model_versions_is_active` - For finding active model

### Table: `prediction_logs` (Enhanced)

Added fields for performance drift detection:

| Column | Type | Description |
|--------|------|-------------|
| `actual_discount` | Float | Ground truth discount (nullable) |
| `has_feedback` | Boolean | Whether feedback was provided |

## API Endpoints

### Drift Detection

#### `GET /v1/drift/check`

Manually trigger drift detection.

**Query Parameters**:
- `data_threshold` (optional): Override data drift threshold
- `performance_threshold` (optional): Override performance drift threshold

**Response**:
```json
{
    "drift_detected": true,
    "data_drift": {
        "drift_detected": true,
        "data_drift_score": 0.45,
        "reference_samples": 1500,
        "current_samples": 350,
        "feature_drifts": {
            "price": {
                "drift_score": 0.45,
                "reference_samples": 1500,
                "current_samples": 350
            },
            "category": {
                "drift_score": 0.32,
                "reference_samples": 1500,
                "current_samples": 350
            }
        }
    },
    "performance_drift": {
        "drift_detected": false,
        "performance_drift_score": null,
        "message": "Insufficient feedback samples: 45 < 100"
    },
    "recommendation": "retrain",
    "checked_at": "2026-01-07T16:00:00"
}
```

#### `GET /v1/drift/history`

Get drift detection history.

**Query Parameters**:
- `limit` (default: 10): Number of records to return

**Response**:
```json
{
    "count": 5,
    "history": [
        {
            "id": "uuid",
            "detection_date": "2026-01-07T02:00:00",
            "data_drift_score": 0.45,
            "performance_drift_score": null,
            "drift_detected": true,
            "recommendation": "retrain",
            "metadata": {...}
        }
    ]
}
```

#### `GET /v1/drift/status`

Get current drift status (latest detection result).

**Response**:
```json
{
    "status": "drift_detected",
    "data_drift_score": 0.45,
    "performance_drift_score": null,
    "recommendation": "retrain",
    "last_check": "2026-01-07T02:00:00",
    "metadata": {...}
}
```

### Retraining

#### `POST /v1/retraining/trigger`

Trigger model retraining.

**Request Body**:
```json
{
    "dataset_path": "data/raw/amazon_sales_dataset.csv",  // Optional
    "drift_triggered": true  // Optional, default: false
}
```

**Response**:
```json
{
    "job_id": "abc-123-def-456",
    "status": "running",
    "message": "Retraining started in background"
}
```

#### `GET /v1/retraining/status/{job_id}`

Get retraining job status.

**Response**:
```json
{
    "status": "completed",
    "started_at": "2026-01-07T16:00:00",
    "completed_at": "2026-01-07T16:15:30",
    "model_version": "v20260107-160000",
    "metrics": {
        "rmse": 4.2,
        "mae": 3.1,
        "r2": 0.89
    },
    "model_path": "/app/models/tuned_catboost_model_20260107_160000.cbm"
}
```

#### `POST /v1/retraining/deploy/{version}`

Deploy a specific model version (make it active).

**Response**:
```json
{
    "status": "deployed",
    "version": "v20260107-160000",
    "model_path": "/app/models/tuned_catboost_model_20260107_160000.cbm",
    "trained_at": "2026-01-07T16:00:00",
    "metrics": {
        "rmse": 4.2,
        "mae": 3.1,
        "r2": 0.89
    }
}
```

#### `GET /v1/retraining/versions`

List all model versions.

**Query Parameters**:
- `limit` (default: 10): Number of versions to return

**Response**:
```json
{
    "count": 3,
    "versions": [
        {
            "id": "uuid",
            "version": "v20260107-160000",
            "model_path": "/app/models/tuned_catboost_model_20260107_160000.cbm",
            "trained_at": "2026-01-07T16:00:00",
            "training_metrics": {...},
            "is_active": true,
            "drift_triggered": true
        }
    ]
}
```

#### `GET /v1/retraining/active`

Get currently active model version.

**Response**:
```json
{
    "id": "uuid",
    "version": "v20260107-160000",
    "model_path": "/app/models/tuned_catboost_model_20260107_160000.cbm",
    "trained_at": "2026-01-07T16:00:00",
    "training_metrics": {...},
    "drift_triggered": true
}
```

## Configuration

### Settings (`src/core/config.py`)

```python
# Drift Detection
drift_check_schedule: str = "0 2 1 * *"  # Monthly on 1st day at 2 AM (cron format)
drift_data_threshold: float = 0.3  # Data drift threshold (0-1)
drift_performance_threshold: float = 0.1  # Performance drift threshold (0-1)
drift_reference_window_days: int = 30  # Reference period for comparison
drift_current_window_days: int = 7  # Current period to check
drift_min_samples: int = 100  # Minimum samples required for drift detection
```

### Environment Variables

You can override these via environment variables:
```bash
DRIFT_CHECK_SCHEDULE="0 2 1 * *"
DRIFT_DATA_THRESHOLD=0.3
DRIFT_PERFORMANCE_THRESHOLD=0.1
DRIFT_REFERENCE_WINDOW_DAYS=30
DRIFT_CURRENT_WINDOW_DAYS=7
DRIFT_MIN_SAMPLES=100
```

## Workflow

### Automated Monthly Detection

1. **Scheduler triggers** (1st of month, 2 AM)
2. **Drift Detection Service**:
   - Reads prediction logs from last 30 days (reference) and last 7 days (current)
   - Compares feature distributions
   - Calculates drift scores
   - Stores results in `drift_logs` table
3. **If drift detected**:
   - Logs warning with recommendation
   - Admin can trigger retraining manually

### Manual Retraining Workflow

1. **Admin triggers retraining** via `POST /v1/retraining/trigger`
2. **Retraining Service**:
   - Loads training dataset
   - Trains new CatBoost model
   - Validates on holdout set
   - Saves model with version (e.g., `v20260107-160000`)
   - Stores metadata in `model_versions` table
3. **Admin reviews metrics** via `GET /v1/retraining/status/{job_id}`
4. **Admin deploys model** via `POST /v1/retraining/deploy/{version}`
5. **Model Loader**:
   - Checks database for active model version
   - Loads new model on next API restart or hot-swap
   - Falls back to default model if active version not found

## Drift Detection Algorithm

### Data Drift Detection

**For Numerical Features**:
```python
# Kolmogorov-Smirnov test
ks_statistic, p_value = stats.ks_2samp(reference_values, current_values)
drift_score = ks_statistic  # 0-1, higher = more drift

# For small samples, use mean difference
if len(samples) < 10:
    drift_score = abs(current_mean - reference_mean) / abs(reference_mean)
```

**For Categorical Features**:
```python
# Total variation distance
ref_proportions = normalize(reference_counts)
curr_proportions = normalize(current_counts)
drift_score = sum(abs(r - c) for r, c in zip(ref_proportions, curr_proportions)) / 2.0
```

### Performance Drift Detection

```python
# Calculate errors for predictions with ground truth
errors = [abs(predicted - actual) for predicted, actual in feedback_data]

mae = mean(errors)
mse = mean([e**2 for e in errors])
rmse = sqrt(mse)

# Compare to baseline
baseline_mae = 5.0  # Expected baseline
performance_drift_score = max(0.0, (mae - baseline_mae) / baseline_mae)
drift_detected = performance_drift_score > threshold
```

## Model Versioning

### Version Naming

Models are versioned using timestamp format:
- Format: `vYYYYMMDD-HHMMSS`
- Example: `v20260107-160000` (trained on Jan 7, 2026 at 4:00 PM)

### Model Storage

- **Path Pattern**: `/app/models/tuned_catboost_model_YYYYMMDD_HHMMSS.cbm`
- **Feature Engineer**: `/app/models/feature_engineer_YYYYMMDD_HHMMSS.pkl`
- **Active Model**: Determined by `is_active=True` in `model_versions` table

### Hot-Swapping

The `ModelLoader` checks the database for the active model version:
1. Query `model_versions` table for `is_active=True`
2. Load model from `model_path`
3. Fall back to default model path if active version not found

**Note**: Model swap requires API restart or hot-reload mechanism.

## Usage Examples

### Check for Drift

```bash
# Manual drift check
curl http://localhost:8000/v1/drift/check

# With custom thresholds
curl "http://localhost:8000/v1/drift/check?data_threshold=0.4&performance_threshold=0.15"
```

### View Drift History

```bash
curl http://localhost:8000/v1/drift/history?limit=20
```

### Trigger Retraining

```bash
# Basic retraining
curl -X POST http://localhost:8000/v1/retraining/trigger \
  -H "Content-Type: application/json" \
  -d '{"drift_triggered": true}'

# With custom dataset
curl -X POST http://localhost:8000/v1/retraining/trigger \
  -H "Content-Type: application/json" \
  -d '{"dataset_path": "data/raw/amazon_sales_dataset.csv"}'
```

### Check Retraining Status

```bash
curl http://localhost:8000/v1/retraining/status/{job_id}
```

### Deploy Model Version

```bash
curl -X POST http://localhost:8000/v1/retraining/deploy/v20260107-160000
```

### List Model Versions

```bash
curl http://localhost:8000/v1/retraining/versions?limit=10
```

## Performance Impact

### Latency Impact: **ZERO on API Requests**

- Drift detection runs as background job (monthly)
- Uses existing prediction logs (no extra writes)
- No blocking operations in prediction path
- Model swap is atomic (no downtime)

### Resource Usage: **MINIMAL**

- **Drift Detection**: ~1-5 seconds monthly (reads recent logs)
- **Retraining**: Runs on-demand (not scheduled)
- **Memory**: ~50MB for drift detection (pandas operations)
- **Database**: Two additional tables (`drift_logs`, `model_versions`)

## Best Practices

### 1. Ground Truth Collection

For performance drift detection, collect ground truth data:

```python
# When actual discount is known, update prediction log
prediction_log.actual_discount = actual_discount_applied
prediction_log.has_feedback = True
await log_repo.log_prediction(prediction_log)
```

### 2. Drift Threshold Tuning

Adjust thresholds based on your domain:
- **Data Drift Threshold**: Lower (0.2) for critical features, higher (0.4) for stable features
- **Performance Drift Threshold**: Lower (0.05) for high-accuracy requirements

### 3. Retraining Strategy

- **After Drift Detection**: Review drift scores before retraining
- **Regular Retraining**: Consider scheduled retraining regardless of drift
- **Model Validation**: Always validate new models before deployment
- **A/B Testing**: Deploy new models gradually if possible

### 4. Monitoring

- Monitor drift detection logs for trends
- Track model version performance
- Set up alerts for high drift scores
- Review retraining metrics regularly

## Troubleshooting

### Drift Detection Returns "Insufficient Samples"

**Cause**: Not enough prediction logs in the time windows.

**Solution**:
- Reduce `drift_min_samples` threshold
- Increase `drift_current_window_days`
- Wait for more predictions to accumulate

### Retraining Fails

**Common Causes**:
- Dataset file not found
- Insufficient training data
- Model training errors

**Solution**:
- Check dataset path exists
- Verify training script works locally
- Review retraining job logs

### Model Not Loading After Deployment

**Cause**: Model file path incorrect or file doesn't exist.

**Solution**:
- Verify `model_path` in `model_versions` table
- Check file exists at that path
- Ensure API has read permissions
- Fall back to default model path

## Related Files

- `src/services/drift_detection_service.py` - Drift detection logic
- `src/services/retraining_service.py` - Model retraining orchestration
- `src/services/scheduler_service.py` - Background scheduler
- `src/api/routers/drift.py` - Drift detection endpoints
- `src/api/routers/retraining.py` - Retraining endpoints
- `src/db/models/drift_log.py` - Drift log model
- `src/db/models/model_version.py` - Model version model
- `src/ml/inference/model_loader.py` - Model versioning support
- `alembic/versions/7f3a8b2c9d1e_add_drift_and_model_versioning.py` - Migration

## Future Enhancements

Potential improvements:
- **Automated Retraining**: Auto-trigger retraining when drift detected
- **A/B Testing**: Deploy multiple model versions simultaneously
- **Rollback Mechanism**: Automatic rollback on performance degradation
- **Alerting**: Email/webhook notifications on drift detection
- **Dashboard**: Visual drift detection and model performance dashboard
- **Feature Importance Tracking**: Monitor which features contribute most to drift
- **Incremental Retraining**: Update models incrementally instead of full retraining

