"""Model version model for tracking model versions."""
from sqlalchemy import Column, String, Boolean, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..postgres import Base


class ModelVersion(Base):
    """Model for tracking ML model versions."""
    
    __tablename__ = "model_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(100), nullable=False, unique=True, index=True)  # e.g., "v1.0.0", "2026-01-07-14-30"
    model_path = Column(String(500), nullable=False)  # Path to model file
    trained_at = Column(DateTime(timezone=True), nullable=False)
    training_metrics = Column(JSON, nullable=True)  # MAE, MSE, R², etc.
    is_active = Column(Boolean, default=False, nullable=False, index=True)  # Currently deployed model
    drift_triggered = Column(Boolean, default=False, nullable=False)  # Retrained due to drift
    created_at = Column(DateTime(timezone=True), server_default=func.now())

