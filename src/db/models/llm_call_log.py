"""LLM call log model for tracking LLM statistics."""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..postgres import Base


class LLMCallLog(Base):
    """Log model for tracking LLM call statistics."""
    
    __tablename__ = "llm_call_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, index=True)
    
    # Token statistics (from Ollama response)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=False)  # LLM processing time
    queue_wait_ms = Column(Integer, nullable=True)  # Time waiting in semaphore
    
    # Model parameters
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    
    # Request metadata
    retry_attempts = Column(Integer, default=0, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Optional link to query_logs (for RAG queries)
    query_log_id = Column(UUID(as_uuid=True), ForeignKey("query_logs.id"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

