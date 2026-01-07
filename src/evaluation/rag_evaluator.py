"""RAG evaluation system."""
from typing import List, Dict, Any
import json
from pathlib import Path

from .metrics import (
    calculate_retrieval_metrics,
    calculate_generation_metrics,
)
from .grounding_checker import GroundingChecker
from ..services.rag_service import RAGService
from ..db.repositories.product_repo import ProductRepository
from ..core.logging import setup_logging

logger = setup_logging()


class RAGEvaluator:
    """Evaluator for RAG system performance."""
    
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.grounding_checker = GroundingChecker()
    
    async def evaluate(
        self,
        test_cases: List[Dict[str, Any]],
        product_repo: ProductRepository
    ) -> Dict[str, Any]:
        """
        Evaluate RAG system on test cases.
        
        Args:
            test_cases: List of test cases with 'question', 'expected_answer', 'relevant_products'
            product_repo: Product repository for fetching products
        
        Returns:
            Dict with evaluation metrics
        """
        retrieval_metrics_list = []
        generation_metrics_list = []
        
        for test_case in test_cases:
            question = test_case["question"]
            expected_answer = test_case.get("expected_answer", "")
            relevant_product_ids = test_case.get("relevant_products", [])
            
            # Get RAG response
            response = await self.rag_service.answer_question(
                question=question,
                product_repo=product_repo,
            )
            
            # Calculate retrieval metrics
            retrieved_ids = [
                p["id"] for p in response["retrieved_products"]
            ]
            retrieval_metrics = calculate_retrieval_metrics(
                retrieved_ids=retrieved_ids,
                relevant_ids=relevant_product_ids,
                k=5,
            )
            retrieval_metrics_list.append(retrieval_metrics)
            
            # Calculate generation metrics
            answer = response["answer"]
            context = self._extract_context(response["retrieved_products"])
            
            generation_metrics = await calculate_generation_metrics(
                question=question,
                answer=answer,
                context=context,
                expected_answer=expected_answer,
                grounding_checker=self.grounding_checker,
            )
            generation_metrics_list.append(generation_metrics)
        
        # Aggregate metrics
        avg_retrieval = self._aggregate_retrieval_metrics(retrieval_metrics_list)
        avg_generation = self._aggregate_generation_metrics(generation_metrics_list)
        
        return {
            "retrieval_metrics": avg_retrieval,
            "generation_metrics": avg_generation,
            "num_test_cases": len(test_cases),
        }
    
    def _extract_context(self, products: List[Dict[str, Any]]) -> str:
        """Extract context string from products."""
        return self.rag_service._build_context(products)
    
    def _aggregate_retrieval_metrics(
        self,
        metrics_list: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """Calculate average retrieval metrics."""
        if not metrics_list:
            return {}
        
        aggregated = {}
        for key in metrics_list[0].keys():
            aggregated[f"avg_{key}"] = sum(m[key] for m in metrics_list) / len(metrics_list)
        
        return aggregated
    
    def _aggregate_generation_metrics(
        self,
        metrics_list: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """Calculate average generation metrics."""
        if not metrics_list:
            return {}
        
        aggregated = {}
        for key in metrics_list[0].keys():
            aggregated[f"avg_{key}"] = sum(m[key] for m in metrics_list) / len(metrics_list)
        
        return aggregated
    
    @staticmethod
    def load_test_dataset(file_path: str) -> List[Dict[str, Any]]:
        """Load test dataset from JSON file."""
        with open(file_path, 'r') as f:
            return json.load(f)




