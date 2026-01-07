"""Log repository for tracking predictions and queries."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from ..models.prediction_log import PredictionLog
from ..models.query_log import QueryLog
from ..models.llm_call_log import LLMCallLog
from ..models.drift_log import DriftLog


class LogRepository:
    """Repository for logging operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_prediction(self, log: PredictionLog) -> PredictionLog:
        """Log a prediction."""
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def log_query(self, log: QueryLog) -> QueryLog:
        """Log a RAG query."""
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def log_llm_call(self, log: LLMCallLog) -> LLMCallLog:
        """Log LLM call statistics (non-blocking async write)."""
        self.session.add(log)
        await self.session.flush()  # Async flush, non-blocking
        return log
    
    async def get_prediction_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None
    ) -> List[PredictionLog]:
        """Get prediction logs within date range for drift detection."""
        query = select(PredictionLog).where(
            and_(
                PredictionLog.created_at >= start_date,
                PredictionLog.created_at <= end_date
            )
        ).order_by(PredictionLog.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def log_drift(self, log: DriftLog) -> DriftLog:
        """Log drift detection result."""
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def get_drift_logs(self, limit: int = 10) -> List[DriftLog]:
        """Get recent drift detection logs."""
        query = select(DriftLog).order_by(DriftLog.detection_date.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())




