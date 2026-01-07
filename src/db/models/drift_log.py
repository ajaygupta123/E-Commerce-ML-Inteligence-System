"""Drift log model for tracking drift detection results."""
from sqlalchemy import Column, Float, Boolean, String, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..postgres import Base


class DriftLog(Base):
    """Log model for tracking drift detection history."""
    
    __tablename__ = "drift_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    data_drift_score = Column(Float, nullable=False)  # Overall data drift score (0-1)
    performance_drift_score = Column(Float, nullable=True)  # Performance drift score if ground truth available
    drift_detected = Column(Boolean, nullable=False, default=False)
    recommendation = Column(String(50), nullable=False)  # "retrain", "monitor", "no_action"
    drift_metadata = Column(JSON, nullable=True)  # Detailed metrics per feature (renamed from 'metadata' - SQLAlchemy reserved)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

