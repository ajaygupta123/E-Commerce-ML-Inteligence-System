"""RAG endpoints."""
from fastapi import APIRouter, Depends, HTTPException
import time
import logging
import asyncio
from typing import Optional, Dict, Any

from ..schemas.rag import QuestionRequest, QuestionResponse
from ...services.rag_service import RAGService
from ...db.repositories.product_repo import ProductRepository
from ...db.repositories.log_repo import LogRepository
from ...db.models.query_log import QueryLog
from ...db.models.llm_call_log import LLMCallLog
from ...db.postgres import AsyncSessionLocal
from ...api.dependencies import get_rag_service, get_product_repo, get_log_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["rag"])


@router.post("/answer_question", response_model=QuestionResponse)
async def answer_question(
    request: QuestionRequest,
    rag_service: RAGService = Depends(get_rag_service),
    product_repo: ProductRepository = Depends(get_product_repo),
    log_repo: LogRepository = Depends(get_log_repo),
):
    """Answer a question using RAG."""
    try:
        start_time = time.time()
        
        # Get answer
        result = await rag_service.answer_question(
            question=request.question,
            top_k=request.top_k,
            product_repo=product_repo,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Log query (non-blocking - don't fail request if logging fails)
        query_log_id = None
        try:
            log_entry = QueryLog(
                query=request.question,
                response=result["answer"],
                retrieved_product_ids=[p["id"] for p in result["retrieved_products"]],
                retrieval_metadata=result["metadata"],
                latency_ms=latency_ms,
            )
            await log_repo.log_query(log_entry)
            query_log_id = log_entry.id  # Get the ID for linking LLM call log
        except Exception as log_error:
            logger.warning(f"Failed to log query: {log_error}", exc_info=True)
        
        # Fire-and-forget LLM stats logging (zero latency impact)
        # Uses its own session since the request session will be closed
        llm_stats = result.get("metadata", {}).get("llm_stats")
        if llm_stats:
            asyncio.create_task(
                _log_llm_call_async(llm_stats, query_log_id)
            )
        
        return QuestionResponse(**result)
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RAG error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _log_llm_call_async(
    llm_stats: Dict[str, Any],
    query_log_id: Optional[str] = None
):
    """
    Background task for logging LLM call statistics.
    
    This is fire-and-forget - failures never affect the request.
    Creates its own database session since the request session will be closed.
    """
    try:
        async with AsyncSessionLocal() as session:
            log_entry = LLMCallLog(
                model_name=llm_stats.get("model_name", "unknown"),
                prompt_tokens=llm_stats.get("prompt_tokens"),
                completion_tokens=llm_stats.get("completion_tokens"),
                total_tokens=llm_stats.get("total_tokens"),
                latency_ms=llm_stats.get("latency_ms", 0),
                queue_wait_ms=llm_stats.get("queue_wait_ms"),
                temperature=llm_stats.get("temperature"),
                max_tokens=llm_stats.get("max_tokens"),
                retry_attempts=llm_stats.get("retry_attempts", 0),
                success=llm_stats.get("success", True),
                error_message=llm_stats.get("error_message"),
                query_log_id=query_log_id,
            )
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to log LLM stats: {e}", exc_info=True)
        # Never raise - this is fire-and-forget, failures don't affect requests



