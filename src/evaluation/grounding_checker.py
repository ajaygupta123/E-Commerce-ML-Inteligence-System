"""Grounding checker for RAG answers."""
from typing import Dict, Any
import re

from ..services.llm_service import LLMService
from ..core.logging import setup_logging

logger = setup_logging()


class GroundingChecker:
    """Checker to verify if answer is grounded in context."""
    
    GROUNDING_PROMPT = """You are a fact-checker. Determine if the answer is supported by the provided context.

Context: {context}

Answer: {answer}

Respond with only "YES" if the answer is fully supported by the context, or "NO" if it contains unsupported claims."""

    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()
        self._use_llm = llm_service is not None
    
    async def check_grounding(self, answer: str, context: str) -> float:
        """
        Check if answer is grounded in context.
        
        Returns:
            Score between 0-1 (1 = fully grounded)
        """
        if not context or not answer:
            return 0.0
        
        if self._use_llm:
            # Use LLM-as-judge for more accurate grounding
            return await self._llm_grounding_check(answer, context)
        else:
            # Fallback to keyword-based check
            return self._keyword_grounding_check(answer, context)
    
    async def _llm_grounding_check(self, answer: str, context: str) -> float:
        """Use LLM to check grounding."""
        try:
            prompt = self.GROUNDING_PROMPT.format(
                context=context[:1000],  # Limit context length
                answer=answer
            )
            
            response, _ = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.0,  # Deterministic
                max_tokens=10,
            )
            
            response_upper = response.strip().upper()
            if "YES" in response_upper:
                return 1.0
            elif "NO" in response_upper:
                return 0.0
            else:
                return 0.5  # Uncertain
        except Exception as e:
            logger.warning(f"LLM grounding check failed: {e}, using keyword check")
            return self._keyword_grounding_check(answer, context)
    
    def _keyword_grounding_check(self, answer: str, context: str) -> float:
        """Simple keyword-based grounding check."""
        # Extract key terms from answer
        answer_terms = set(re.findall(r'\b\w{4,}\b', answer.lower()))
        context_lower = context.lower()
        
        if not answer_terms:
            return 0.5
        
        # Check how many terms appear in context
        grounded_terms = sum(1 for term in answer_terms if term in context_lower)
        return grounded_terms / len(answer_terms)




