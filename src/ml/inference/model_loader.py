"""Model loader with abstraction for S3/MinIO swap."""
from pathlib import Path
from typing import Optional
from catboost import CatBoostRegressor

from ...core.config import settings
from ...core.logging import setup_logging
from ...core.exceptions import ModelNotFoundError

logger = setup_logging()


class ModelLoader:
    """
    Model loader for CatBoost models with versioning support.
    
    Loads from local filesystem, with support for:
    - Model versioning (checks database for active version)
    - Fallback to default model path
    - Hot-swapping models
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.model_path
        self._active_model_path: Optional[str] = None
    
    async def get_active_model_path(self) -> Optional[str]:
        """
        Get active model path from database.
        
        Returns:
            Path to active model, or None if no active version found
        """
        try:
            from ...db.postgres import AsyncSessionLocal
            from ...db.models.model_version import ModelVersion
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ModelVersion).where(ModelVersion.is_active == True)
                )
                model_version = result.scalar_one_or_none()
                
                if model_version and Path(model_version.model_path).exists():
                    return model_version.model_path
        except Exception as e:
            logger.warning(f"Could not fetch active model version: {e}, using default path")
        
        return None
    
    async def load_model(self) -> CatBoostRegressor:
        """
        Load CatBoost model from filesystem.
        
        Checks for active model version first, falls back to default path.
        """
        # Try to get active model version
        active_path = await self.get_active_model_path()
        model_path_to_load = active_path or self.model_path
        
        model_file = Path(model_path_to_load)
        
        if not model_file.exists():
            # Fallback to default if active version doesn't exist
            if active_path and model_path_to_load != self.model_path:
                logger.warning(f"Active model not found: {active_path}, falling back to default")
                model_file = Path(self.model_path)
            
            if not model_file.exists():
                raise ModelNotFoundError(
                    f"Model file not found: {model_path_to_load}. "
                    "Please train the model first using scripts/train_models.py"
                )
        
        logger.info(f"Loading model from {model_file}")
        model = CatBoostRegressor()
        model.load_model(str(model_file))
        logger.info("Model loaded successfully")
        
        self._active_model_path = str(model_file)
        return model
    
    def load_model_sync(self) -> CatBoostRegressor:
        """
        Synchronous version of load_model (for backward compatibility).
        
        Uses default model path without checking database.
        """
        model_file = Path(self.model_path)
        
        if not model_file.exists():
            raise ModelNotFoundError(
                f"Model file not found: {self.model_path}. "
                "Please train the model first using scripts/train_models.py"
            )
        
        logger.info(f"Loading model from {self.model_path}")
        model = CatBoostRegressor()
        model.load_model(str(model_file))
        logger.info("Model loaded successfully")
        
        return model
    
    def model_exists(self) -> bool:
        """Check if model file exists."""
        return Path(self.model_path).exists()




