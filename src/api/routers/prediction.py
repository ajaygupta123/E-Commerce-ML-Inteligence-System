"""Prediction endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
import logging

from ..schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    ExplanationResponse,
)
from ...services.prediction_service import PredictionService
from ...db.repositories.log_repo import LogRepository
from ...db.models.prediction_log import PredictionLog
from ...api.dependencies import get_prediction_service, get_log_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["prediction"])


@router.post("/predict_discount", response_model=PredictionResponse)
async def predict_discount(
    request: PredictionRequest,
    prediction_service: PredictionService = Depends(get_prediction_service),
    log_repo: LogRepository = Depends(get_log_repo),
):
    """Predict discount percentage for a product."""
    try:
        # Convert request to features dict
        features = request.dict(exclude_none=True)
        
        # Make prediction
        result = prediction_service.predict(features, include_explanation=False)
        
        # Log prediction (non-blocking - don't fail request if logging fails)
        try:
            log_entry = PredictionLog(
                input_features=features,
                predicted_discount=result["predicted_discount"],
                confidence_score=result["confidence_score"],
            )
            await log_repo.log_prediction(log_entry)
        except Exception as log_error:
            logger.warning(f"Failed to log prediction: {log_error}", exc_info=True)
        
        return PredictionResponse(**result)
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain", response_model=ExplanationResponse)
async def explain_prediction(
    request: PredictionRequest,
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """Get prediction with SHAP explanation."""
    try:
        features = request.dict(exclude_none=True)
        result = prediction_service.predict(features, include_explanation=True)
        
        return ExplanationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



