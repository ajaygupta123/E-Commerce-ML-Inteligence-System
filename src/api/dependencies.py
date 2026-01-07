"""Dependency injection for FastAPI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.postgres import get_db_session
from ..db.repositories.product_repo import ProductRepository
from ..db.repositories.log_repo import LogRepository
from ..services.prediction_service import PredictionService
from ..services.rag_service import RAGService
from ..services.cache_service import get_cache_service


def get_product_repo(
    session: AsyncSession = Depends(get_db_session)
) -> ProductRepository:
    """Get product repository."""
    return ProductRepository(session)


def get_log_repo(
    session: AsyncSession = Depends(get_db_session)
) -> LogRepository:
    """Get log repository."""
    return LogRepository(session)


def get_prediction_service() -> PredictionService:
    """Get prediction service (singleton)."""
    # In production, use proper dependency injection container
    if not hasattr(get_prediction_service, '_instance'):
        get_prediction_service._instance = PredictionService()
    return get_prediction_service._instance


def get_rag_service() -> RAGService:
    """Get RAG service (singleton)."""
    if not hasattr(get_rag_service, '_instance'):
        get_rag_service._instance = RAGService()
    return get_rag_service._instance




