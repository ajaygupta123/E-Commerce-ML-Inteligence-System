# RAG System Evaluation

## Overview

This document describes the evaluation metrics and methodology for the RAG (Retrieval-Augmented Generation) system.

## Metrics Implemented

### Retrieval Metrics

#### Precision@K
**Definition**: Fraction of retrieved products that are relevant.

**Formula**: `Precision@K = (Relevant Retrieved) / K`

**Interpretation**: 
- Higher is better (0-1 scale)
- Measures retrieval quality
- K=5 in our implementation

#### Recall@K
**Definition**: Fraction of relevant products that were retrieved.

**Formula**: `Recall@K = (Relevant Retrieved) / (Total Relevant)`

**Interpretation**:
- Higher is better (0-1 scale)
- Measures retrieval completeness
- K=5 in our implementation

#### Mean Reciprocal Rank (MRR)
**Definition**: Reciprocal of the rank of the first relevant result.

**Formula**: `MRR = 1 / rank_of_first_relevant`

**Interpretation**:
- Higher is better (0-1 scale)
- Measures how quickly we find relevant results
- 1.0 = first result is relevant

### Generation Metrics

#### Grounding Score
**Definition**: Is the answer supported by the retrieved context?

**Method**: 
- LLM-as-judge (primary)
- Keyword-based fallback

**Interpretation**:
- 1.0 = Fully grounded
- 0.0 = Not grounded
- Measures hallucination prevention

#### Factuality Rate
**Definition**: Are expected facts present in the answer?

**Method**: Keyword overlap between expected and generated answers.

**Interpretation**:
- 1.0 = All facts present
- 0.0 = No facts present
- Measures factual correctness

#### Hallucination Rate
**Definition**: Fraction of unsupported claims in the answer.

**Method**: Check if answer sentences contain information not in context.

**Interpretation**:
- 0.0 = No hallucinations
- 1.0 = All claims unsupported
- Lower is better

#### Answer Relevance
**Definition**: Does the answer address the question?

**Method**: Keyword overlap between question and answer.

**Interpretation**:
- 1.0 = Fully relevant
- 0.0 = Not relevant
- Measures answer quality

## Evaluation Dataset

Location: `data/evaluation/rag_test_set.json`

### Test Case Format
```json
{
  "question": "What are the cheapest products?",
  "expected_answer": "Products with lowest prices",
  "relevant_products": ["product-id-1", "product-id-2"]
}
```

### Test Coverage
- Product comparisons
- Price queries
- Feature questions
- Category searches
- Rating-based queries

## Evaluation Results

[To be filled after running evaluation]

### Example Results Structure
```json
{
  "retrieval_metrics": {
    "avg_precision_at_k": 0.85,
    "avg_recall_at_k": 0.72,
    "avg_mrr": 0.78
  },
  "generation_metrics": {
    "avg_grounding_score": 0.92,
    "avg_factuality_rate": 0.88,
    "avg_hallucination_rate": 0.05,
    "avg_answer_relevance": 0.90
  },
  "num_test_cases": 10
}
```

## Benchmarking

### Baseline Comparison
- **Simple Retrieval**: BM25-based retrieval
- **No RAG**: Direct LLM without context
- **Our RAG**: Qdrant + Llama 3.2 3B

### Target Metrics
- Precision@5: > 0.80
- Recall@5: > 0.70
- Grounding Score: > 0.90
- Hallucination Rate: < 0.10

## Continuous Evaluation

### Monitoring
- Log all queries and responses
- Track metrics over time
- Alert on degradation

### Improvement Strategies
1. **Better Embeddings**: Upgrade to larger models
2. **Reranking**: Add second-stage reranking
3. **Hybrid Search**: Combine semantic + keyword search
4. **Prompt Engineering**: Optimize system prompts
5. **Context Compression**: Summarize retrieved context

## Limitations

1. **Evaluation Dataset Size**: Limited test cases
2. **Subjective Metrics**: Some metrics rely on heuristics
3. **Domain Specificity**: Metrics tuned for e-commerce
4. **LLM-as-Judge**: May have biases

## Future Work

- [ ] Human evaluation
- [ ] Larger test dataset
- [ ] Multi-turn conversation evaluation
- [ ] A/B testing framework
- [ ] Real-time monitoring dashboard




