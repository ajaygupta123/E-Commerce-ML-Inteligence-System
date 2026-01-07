"""Query log model for tracking RAG queries."""
from sqlalchemy import Column, String, Text, JSON, DateTime, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..postgres import Base


class QueryLog(Base):
    """Log model for tracking RAG queries and responses."""
    
    __tablename__ = "query_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    response = Column(Text)
    retrieved_product_ids = Column(JSON)  # List of product IDs retrieved
    retrieval_metadata = Column(JSON)  # Scores, distances, etc.
    generation_metadata = Column(JSON)  # LLM metadata
    latency_ms = Column(Integer)  # Total latency in milliseconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())




