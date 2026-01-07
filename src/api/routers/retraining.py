"""Retraining endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

from ...services.retraining_service import RetrainingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["retraining"])

# Global retraining service instance
_retraining_service: Optional[RetrainingService] = None


def get_retraining_service() -> RetrainingService:
    """Dependency for retraining service (singleton)."""
    global _retraining_service
    if _retraining_service is None:
        _retraining_service = RetrainingService()
    return _retraining_service


@router.post("/retraining/trigger")
async def trigger_retraining(
    dataset_path: Optional[str] = None,
    drift_triggered: bool = False,
    retraining_service: RetrainingService = Depends(get_retraining_service),
):
    """
    Trigger model retraining.
    
    Args:
        dataset_path: Optional path to dataset (defaults to configured path)
        drift_triggered: Whether retraining was triggered by drift detection
    
    Returns:
        Dict with job_id and status
    """
    try:
        result = await retraining_service.trigger_retraining(
            dataset_path=dataset_path,
            drift_triggered=drift_triggered
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering retraining: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retraining/status/{job_id}")
async def get_retraining_status(
    job_id: str,
    retraining_service: RetrainingService = Depends(get_retraining_service),
):
    """Get status of a retraining job."""
    status = retraining_service.get_training_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return status


@router.post("/retraining/deploy/{version}")
async def deploy_model_version(
    version: str,
    retraining_service: RetrainingService = Depends(get_retraining_service),
):
    """
    Deploy a specific model version (make it active).
    
    This will:
    1. Deactivate current active model
    2. Activate the specified version
    3. The model loader will use the new version on next load
    """
    try:
        result = await retraining_service.deploy_model_version(version)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deploying model version: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retraining/versions")
async def get_model_versions(
    limit: int = 10,
    retraining_service: RetrainingService = Depends(get_retraining_service),
):
    """Get list of model versions."""
    try:
        result = await retraining_service.get_model_versions(limit=limit)
        return result
    except Exception as e:
        logger.error(f"Error fetching model versions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retraining/active")
async def get_active_model(
    retraining_service: RetrainingService = Depends(get_retraining_service),
):
    """Get currently active model version."""
    try:
        result = await retraining_service.get_active_model()
        if not result:
            return {
                "status": "no_active_model",
                "message": "No active model version found"
            }
        return result
    except Exception as e:
        logger.error(f"Error fetching active model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

