"""Retraining service for model retraining orchestration."""
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import asyncio
import uuid

from ..ml.training.train_catboost import train_catboost
from ..core.config import settings
from ..core.logging import setup_logging
from ..db.postgres import AsyncSessionLocal
from ..db.models.model_version import ModelVersion

logger = setup_logging()


class RetrainingService:
    """Service for orchestrating model retraining."""
    
    def __init__(self):
        self.training_jobs: Dict[str, Dict[str, Any]] = {}  # job_id -> job_status
    
    async def trigger_retraining(
        self,
        dataset_path: Optional[str] = None,
        drift_triggered: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger model retraining in background.
        
        Args:
            dataset_path: Path to dataset (defaults to settings)
            drift_triggered: Whether retraining was triggered by drift detection
        
        Returns:
            Dict with job_id and status
        """
        job_id = str(uuid.uuid4())
        
        # Default dataset path
        if dataset_path is None:
            dataset_path = "data/raw/amazon_sales_dataset.csv"
        
        # Check if dataset exists
        if not Path(dataset_path).exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        # Initialize job status
        self.training_jobs[job_id] = {
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "drift_triggered": drift_triggered,
            "dataset_path": dataset_path,
            "error": None,
            "model_version": None,
            "metrics": None
        }
        
        # Start training in background
        asyncio.create_task(self._train_model_async(job_id, dataset_path, drift_triggered))
        
        return {
            "job_id": job_id,
            "status": "running",
            "message": "Retraining started in background"
        }
    
    async def _train_model_async(
        self,
        job_id: str,
        dataset_path: str,
        drift_triggered: bool
    ):
        """Background task for model training."""
        try:
            logger.info(f"Starting model retraining job {job_id}")
            
            # Generate version string (timestamp-based)
            version = datetime.utcnow().strftime("v%Y%m%d-%H%M%S")
            
            # Generate model path with version
            model_dir = Path(settings.model_path).parent
            model_filename = f"tuned_catboost_model_{version.replace('v', '')}.cbm"
            model_path = str(model_dir / model_filename)
            feature_engineer_path = str(model_dir / f"feature_engineer_{version.replace('v', '')}.pkl")
            
            # Run training (blocking, but in background task)
            # Use asyncio.to_thread to run sync training in thread pool
            result = await asyncio.to_thread(
                train_catboost,
                dataset_path=dataset_path,
                model_output_path=model_path,
                feature_engineer_path=feature_engineer_path
            )
            
            # Save model version to database
            async with AsyncSessionLocal() as session:
                model_version = ModelVersion(
                    version=version,
                    model_path=model_path,
                    trained_at=datetime.utcnow(),
                    training_metrics=result.get("metrics"),
                    is_active=False,  # Not active until manually deployed
                    drift_triggered=drift_triggered
                )
                session.add(model_version)
                await session.commit()
                
                # Update job status
                self.training_jobs[job_id].update({
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "model_version": version,
                    "metrics": result.get("metrics"),
                    "model_path": model_path
                })
                
                logger.info(f"Model retraining completed: {version}")
                logger.info(f"Metrics: {result.get('metrics')}")
        
        except Exception as e:
            logger.error(f"Model retraining failed for job {job_id}: {e}", exc_info=True)
            self.training_jobs[job_id].update({
                "status": "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "error": str(e)
            })
    
    def get_training_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a training job."""
        return self.training_jobs.get(job_id)
    
    async def deploy_model_version(self, version: str) -> Dict[str, Any]:
        """
        Deploy a specific model version (make it active).
        
        Args:
            version: Model version string
        
        Returns:
            Dict with deployment status
        """
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, update
            
            # Get model version
            result = await session.execute(
                select(ModelVersion).where(ModelVersion.version == version)
            )
            model_version = result.scalar_one_or_none()
            
            if not model_version:
                raise ValueError(f"Model version not found: {version}")
            
            # Check if model file exists
            if not Path(model_version.model_path).exists():
                raise FileNotFoundError(f"Model file not found: {model_version.model_path}")
            
            # Deactivate all other versions
            await session.execute(
                update(ModelVersion).values(is_active=False)
            )
            
            # Activate this version
            model_version.is_active = True
            await session.commit()
            
            logger.info(f"Deployed model version: {version}")
            
            return {
                "status": "deployed",
                "version": version,
                "model_path": model_version.model_path,
                "trained_at": model_version.trained_at.isoformat(),
                "metrics": model_version.training_metrics
            }
    
    async def get_model_versions(self, limit: int = 10) -> Dict[str, Any]:
        """Get list of model versions."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(ModelVersion)
                .order_by(ModelVersion.trained_at.desc())
                .limit(limit)
            )
            versions = list(result.scalars().all())
            
            return {
                "count": len(versions),
                "versions": [
                    {
                        "id": str(v.id),
                        "version": v.version,
                        "model_path": v.model_path,
                        "trained_at": v.trained_at.isoformat(),
                        "training_metrics": v.training_metrics,
                        "is_active": v.is_active,
                        "drift_triggered": v.drift_triggered
                    }
                    for v in versions
                ]
            }
    
    async def get_active_model(self) -> Optional[Dict[str, Any]]:
        """Get currently active model version."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(ModelVersion).where(ModelVersion.is_active == True)
            )
            model_version = result.scalar_one_or_none()
            
            if not model_version:
                return None
            
            return {
                "id": str(model_version.id),
                "version": model_version.version,
                "model_path": model_version.model_path,
                "trained_at": model_version.trained_at.isoformat(),
                "training_metrics": model_version.training_metrics,
                "drift_triggered": model_version.drift_triggered
            }

