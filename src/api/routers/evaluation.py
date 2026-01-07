"""RAG evaluation endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from ..schemas.rag import EvaluationRequest, EvaluationResponse
from ...evaluation.rag_evaluator import RAGEvaluator
from ...services.rag_service import RAGService
from ...db.repositories.product_repo import ProductRepository
from ...api.dependencies import get_rag_service, get_product_repo

router = APIRouter(prefix="/v1", tags=["evaluation"])


@router.post("/evaluate_rag", response_model=EvaluationResponse)
async def evaluate_rag(
    request: EvaluationRequest,
    rag_service: RAGService = Depends(get_rag_service),
    product_repo: ProductRepository = Depends(get_product_repo),
):
    """Evaluate RAG system performance."""
    try:
        evaluator = RAGEvaluator(rag_service)
        results = await evaluator.evaluate(
            test_cases=request.test_cases,
            product_repo=product_repo,
        )
        
        return EvaluationResponse(**results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




