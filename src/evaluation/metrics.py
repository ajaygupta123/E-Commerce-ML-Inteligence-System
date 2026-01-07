"""RAG evaluation metrics."""
from typing import List, Dict, Any
import re


def calculate_retrieval_metrics(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int = 5
) -> Dict[str, float]:
    """
    Calculate retrieval metrics.
    
    Args:
        retrieved_ids: List of retrieved product IDs
        relevant_ids: List of relevant product IDs
        k: Number of top results to consider
    
    Returns:
        Dict with precision@k, recall@k, and MRR
    """
    # Take top k
    retrieved_top_k = retrieved_ids[:k]
    relevant_set = set(relevant_ids)
    
    # Precision@K: fraction of retrieved that are relevant
    if len(retrieved_top_k) == 0:
        precision_at_k = 0.0
    else:
        relevant_retrieved = sum(1 for pid in retrieved_top_k if pid in relevant_set)
        precision_at_k = relevant_retrieved / len(retrieved_top_k)
    
    # Recall@K: fraction of relevant that were retrieved
    if len(relevant_set) == 0:
        recall_at_k = 1.0 if len(retrieved_top_k) == 0 else 0.0
    else:
        relevant_retrieved = sum(1 for pid in retrieved_top_k if pid in relevant_set)
        recall_at_k = relevant_retrieved / len(relevant_set)
    
    # MRR: Mean Reciprocal Rank of first relevant result
    mrr = 0.0
    for i, pid in enumerate(retrieved_top_k, 1):
        if pid in relevant_set:
            mrr = 1.0 / i
            break
    
    return {
        "precision_at_k": precision_at_k,
        "recall_at_k": recall_at_k,
        "mrr": mrr,
    }


async def calculate_generation_metrics(
    question: str,
    answer: str,
    context: str,
    expected_answer: str,
    grounding_checker: Any,
) -> Dict[str, float]:
    """
    Calculate generation metrics.
    
    Args:
        question: User question
        answer: Generated answer
        context: Retrieved context
        expected_answer: Expected answer (for factuality)
        grounding_checker: Grounding checker instance
    
    Returns:
        Dict with grounding, factuality, hallucination, and relevance scores
    """
    # Grounding score: Is answer based on context?
    grounding_score = await grounding_checker.check_grounding(answer, context)
    
    # Factuality rate: Are expected facts present?
    factuality_rate = _calculate_factuality(answer, expected_answer)
    
    # Hallucination rate: Unsupported claims?
    hallucination_rate = _calculate_hallucination(answer, context)
    
    # Answer relevance: Does it answer the question?
    answer_relevance = _calculate_relevance(question, answer)
    
    return {
        "grounding_score": grounding_score,
        "factuality_rate": factuality_rate,
        "hallucination_rate": hallucination_rate,
        "answer_relevance": answer_relevance,
    }


def _calculate_factuality(answer: str, expected_answer: str) -> float:
    """
    Calculate factuality rate (0-1).
    
    Simplified: Check if key facts from expected answer are in generated answer.
    """
    if not expected_answer:
        return 0.5  # Neutral if no expected answer
    
    # Extract key facts (simplified - use keywords)
    expected_keywords = set(re.findall(r'\b\w+\b', expected_answer.lower()))
    answer_keywords = set(re.findall(r'\b\w+\b', answer.lower()))
    
    if not expected_keywords:
        return 0.5
    
    overlap = len(expected_keywords & answer_keywords)
    return min(1.0, overlap / len(expected_keywords))


def _calculate_hallucination(answer: str, context: str) -> float:
    """
    Calculate hallucination rate (0-1).
    
    Higher score = more hallucinations (unsupported claims).
    """
    if not context:
        return 1.0  # All unsupported if no context
    
    # Extract claims from answer (simplified)
    answer_sentences = re.split(r'[.!?]+', answer)
    context_lower = context.lower()
    
    unsupported = 0
    total = 0
    
    for sentence in answer_sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:  # Skip very short sentences
            continue
        
        total += 1
        # Check if sentence contains information not in context
        sentence_keywords = set(re.findall(r'\b\w{4,}\b', sentence.lower()))
        context_keywords = set(re.findall(r'\b\w{4,}\b', context_lower))
        
        # If significant keywords not in context, might be hallucination
        if sentence_keywords and len(sentence_keywords - context_keywords) > len(sentence_keywords) * 0.5:
            unsupported += 1
    
    if total == 0:
        return 0.0
    
    return unsupported / total


def _calculate_relevance(question: str, answer: str) -> float:
    """
    Calculate answer relevance (0-1).
    
    Simplified: Check if answer contains question keywords.
    """
    question_keywords = set(re.findall(r'\b\w{4,}\b', question.lower()))
    answer_lower = answer.lower()
    
    if not question_keywords:
        return 0.5
    
    matched = sum(1 for kw in question_keywords if kw in answer_lower)
    return min(1.0, matched / len(question_keywords))




