"""Prediction log model for tracking ML predictions."""
from sqlalchemy import Column, Integer, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..postgres import Base


class PredictionLog(Base):
    """Log model for tracking discount predictions."""
    
    __tablename__ = "prediction_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    input_features = Column(JSON, nullable=False)  # Features used for prediction
    predicted_discount = Column(Float, nullable=False)
    confidence_score = Column(Float)
    shap_values = Column(JSON)  # SHAP explanation values
    actual_discount = Column(Float, nullable=True)  # Ground truth for performance drift detection
    has_feedback = Column(Boolean, default=False, nullable=False)  # Whether feedback was provided
    created_at = Column(DateTime(timezone=True), server_default=func.now())




