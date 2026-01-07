"""Drift detection service for monitoring model performance."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats

from ..db.repositories.log_repo import LogRepository
from ..db.models.prediction_log import PredictionLog
from ..core.config import settings
from ..core.logging import setup_logging

logger = setup_logging()


class DriftDetectionService:
    """Service for detecting data and performance drift."""
    
    def __init__(self, log_repo: LogRepository):
        self.log_repo = log_repo
    
    async def detect_data_drift(
        self,
        reference_window_days: int = None,
        current_window_days: int = None
    ) -> Dict[str, Any]:
        """
        Detect data drift by comparing feature distributions.
        
        Args:
            reference_window_days: Days to look back for reference period
            current_window_days: Days to look back for current period
        
        Returns:
            Dict with drift scores per feature and overall score
        """
        reference_window = reference_window_days or settings.drift_reference_window_days
        current_window = current_window_days or settings.drift_current_window_days
        
        end_date = datetime.utcnow()
        reference_start = end_date - timedelta(days=reference_window)
        current_start = end_date - timedelta(days=current_window)
        
        # Get reference period logs
        reference_logs = await self.log_repo.get_prediction_logs(
            reference_start,
            end_date - timedelta(days=current_window)
        )
        
        # Get current period logs
        current_logs = await self.log_repo.get_prediction_logs(
            current_start,
            end_date
        )
        
        if len(reference_logs) < settings.drift_min_samples:
            return {
                "drift_detected": False,
                "data_drift_score": 0.0,
                "message": f"Insufficient reference samples: {len(reference_logs)} < {settings.drift_min_samples}",
                "feature_drifts": {}
            }
        
        if len(current_logs) < settings.drift_min_samples:
            return {
                "drift_detected": False,
                "data_drift_score": 0.0,
                "message": f"Insufficient current samples: {len(current_logs)} < {settings.drift_min_samples}",
                "feature_drifts": {}
            }
        
        # Extract features from logs
        reference_features = self._extract_features(reference_logs)
        current_features = self._extract_features(current_logs)
        
        if not reference_features or not current_features:
            return {
                "drift_detected": False,
                "data_drift_score": 0.0,
                "message": "No features found in logs",
                "feature_drifts": {}
            }
        
        # Compare distributions
        feature_drifts = {}
        max_drift_score = 0.0
        
        # Get common features
        all_features = set(reference_features[0].keys()) & set(current_features[0].keys())
        
        for feature in all_features:
            ref_values = [f[feature] for f in reference_features if feature in f and f[feature] is not None]
            curr_values = [f[feature] for f in current_features if feature in f and f[feature] is not None]
            
            if not ref_values or not curr_values:
                continue
            
            # Skip if all values are the same
            if len(set(ref_values)) == 1 and len(set(curr_values)) == 1:
                continue
            
            # Determine if numerical or categorical
            try:
                ref_numeric = [float(v) for v in ref_values]
                curr_numeric = [float(v) for v in curr_values]
                
                # Numerical feature: Use Kolmogorov-Smirnov test
                if len(ref_numeric) > 10 and len(curr_numeric) > 10:
                    ks_statistic, p_value = stats.ks_2samp(ref_numeric, curr_numeric)
                    drift_score = ks_statistic  # 0-1, higher = more drift
                else:
                    # Small sample: Use mean difference
                    ref_mean = np.mean(ref_numeric)
                    curr_mean = np.mean(curr_numeric)
                    if ref_mean != 0:
                        drift_score = abs(curr_mean - ref_mean) / abs(ref_mean)
                    else:
                        drift_score = abs(curr_mean) if curr_mean != 0 else 0.0
                
            except (ValueError, TypeError):
                # Categorical feature: Use chi-square test
                ref_counts = pd.Series(ref_values).value_counts()
                curr_counts = pd.Series(curr_values).value_counts()
                
                # Get all categories
                all_cats = set(ref_counts.index) | set(curr_counts.index)
                
                # Create frequency vectors
                ref_freq = [ref_counts.get(cat, 0) for cat in all_cats]
                curr_freq = [curr_counts.get(cat, 0) for cat in all_cats]
                
                # Normalize to proportions
                ref_total = sum(ref_freq)
                curr_total = sum(curr_freq)
                
                if ref_total > 0 and curr_total > 0:
                    ref_prop = [f / ref_total for f in ref_freq]
                    curr_prop = [f / curr_total for f in curr_freq]
                    # Use total variation distance (simpler than chi-square)
                    drift_score = sum(abs(r - c) for r, c in zip(ref_prop, curr_prop)) / 2.0
                else:
                    drift_score = 0.0
            
            feature_drifts[feature] = {
                "drift_score": float(drift_score),
                "reference_samples": len(ref_values),
                "current_samples": len(curr_values)
            }
            
            max_drift_score = max(max_drift_score, drift_score)
        
        overall_drift_score = max_drift_score
        drift_detected = overall_drift_score > settings.drift_data_threshold
        
        return {
            "drift_detected": drift_detected,
            "data_drift_score": float(overall_drift_score),
            "reference_samples": len(reference_logs),
            "current_samples": len(current_logs),
            "feature_drifts": feature_drifts,
            "reference_window_days": reference_window,
            "current_window_days": current_window
        }
    
    async def detect_performance_drift(
        self,
        min_samples: int = None,
        current_window_days: int = None
    ) -> Dict[str, Any]:
        """
        Detect performance drift by comparing prediction errors.
        
        Requires ground truth (actual_discount) in prediction logs.
        
        Args:
            min_samples: Minimum samples with feedback required
            current_window_days: Days to look back for current period
        
        Returns:
            Dict with performance metrics and drift flag
        """
        min_samples = min_samples or settings.drift_min_samples
        current_window = current_window_days or settings.drift_current_window_days
        
        end_date = datetime.utcnow()
        current_start = end_date - timedelta(days=current_window)
        
        # Get logs with feedback (ground truth)
        all_logs = await self.log_repo.get_prediction_logs(current_start, end_date)
        feedback_logs = [log for log in all_logs if log.has_feedback and log.actual_discount is not None]
        
        if len(feedback_logs) < min_samples:
            return {
                "drift_detected": False,
                "performance_drift_score": None,
                "message": f"Insufficient feedback samples: {len(feedback_logs)} < {min_samples}",
                "metrics": {}
            }
        
        # Calculate errors
        errors = []
        for log in feedback_logs:
            error = abs(log.predicted_discount - log.actual_discount)
            errors.append(error)
        
        mae = np.mean(errors)
        mse = np.mean([e**2 for e in errors])
        rmse = np.sqrt(mse)
        
        # For now, compare against a baseline (could be improved with reference period)
        # Assume baseline MAE of 5.0 (adjust based on your model's performance)
        baseline_mae = 5.0
        performance_drift_score = max(0.0, (mae - baseline_mae) / baseline_mae) if baseline_mae > 0 else 0.0
        
        drift_detected = performance_drift_score > settings.drift_performance_threshold
        
        return {
            "drift_detected": drift_detected,
            "performance_drift_score": float(performance_drift_score),
            "samples": len(feedback_logs),
            "metrics": {
                "mae": float(mae),
                "mse": float(mse),
                "rmse": float(rmse),
                "baseline_mae": baseline_mae
            }
        }
    
    async def check_drift(
        self,
        data_drift_threshold: float = None,
        performance_drift_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Comprehensive drift check combining data and performance drift.
        
        Returns:
            Dict with overall drift status and recommendations
        """
        data_drift_threshold = data_drift_threshold or settings.drift_data_threshold
        performance_drift_threshold = performance_drift_threshold or settings.drift_performance_threshold
        
        # Check data drift
        data_drift_result = await self.detect_data_drift()
        
        # Check performance drift (if ground truth available)
        performance_drift_result = await self.detect_performance_drift()
        
        # Determine overall drift status
        data_drift_detected = data_drift_result.get("drift_detected", False)
        performance_drift_detected = performance_drift_result.get("drift_detected", False)
        
        overall_drift_detected = data_drift_detected or performance_drift_detected
        
        # Determine recommendation
        if overall_drift_detected:
            if data_drift_detected and performance_drift_detected:
                recommendation = "retrain"
            elif data_drift_detected:
                recommendation = "retrain"  # Data drift suggests retraining
            else:
                recommendation = "monitor"  # Performance drift only, monitor closely
        else:
            recommendation = "no_action"
        
        return {
            "drift_detected": overall_drift_detected,
            "data_drift": data_drift_result,
            "performance_drift": performance_drift_result,
            "recommendation": recommendation,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    def _extract_features(self, logs: List[PredictionLog]) -> List[Dict[str, Any]]:
        """Extract features from prediction logs."""
        features = []
        for log in logs:
            if log.input_features:
                features.append(log.input_features)
        return features

