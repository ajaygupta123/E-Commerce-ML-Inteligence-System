# API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Currently no authentication required. In production, implement JWT or API keys.

## Endpoints

### Health & Status

#### GET /health
Basic health check.

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### GET /ready
Readiness check (verifies database, model, and services).

**Response**:
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "qdrant": true,
    "model": true,
    "ollama": true
  }
}
```

**Status Codes**:
- 200: All systems ready
- 503: One or more systems not ready

#### GET /metrics
Prometheus metrics endpoint.

**Response**: Prometheus format text

---

### Prediction Endpoints

#### POST /v1/predict_discount
Predict discount percentage for a product.

**Request Body**:
```json
{
  "price": 100.0,
  "category": "Electronics",
  "rating": 4.5,
  "num_reviews": 1000,
  "attributes": {
    "color": "black",
    "size": "large"
  }
}
```

**Required Fields**:
- `price` (float): Product price (> 0)
- `category` (string): Product category

**Optional Fields**:
- `rating` (float): Rating 0-5
- `num_reviews` (int): Number of reviews
- `attributes` (object): Additional attributes

**Response**:
```json
{
  "predicted_discount": 15.5,
  "confidence_score": 0.85,
  "features": {
    "price": 100.0,
    "category": "Electronics",
    "rating": 4.5
  }
}
```

**Status Codes**:
- 200: Success
- 400: Invalid input
- 500: Model error

#### POST /v1/explain
Get prediction with SHAP explanation.

**Request Body**: Same as `/v1/predict_discount`

**Response**:
```json
{
  "predicted_discount": 15.5,
  "confidence_score": 0.85,
  "explanation": {
    "shap_values": {
      "price": 2.3,
      "category": -1.5,
      "rating": 0.8
    },
    "base_value": 12.0,
    "feature_importance": {
      "price": 2.3,
      "rating": 0.8,
      "category": 1.5
    }
  },
  "features": {...}
}
```

---

### RAG Endpoints

#### POST /v1/answer_question
Answer a question using RAG.

**Request Body**:
```json
{
  "question": "What are the cheapest products in electronics?",
  "top_k": 5
}
```

**Fields**:
- `question` (string): User question (1-1000 chars)
- `top_k` (int): Number of products to retrieve (1-20, default: 5)

**Response**:
```json
{
  "answer": "Based on the product catalog, the cheapest electronics products are...",
  "retrieved_products": [
    {
      "id": "uuid",
      "name": "Product Name",
      "category": "Electronics",
      "price": 29.99,
      "rating": 4.5,
      "description": "Product description..."
    }
  ],
  "metadata": {
    "retrieved_count": 5,
    "retrieval_scores": [0.95, 0.92, 0.88, 0.85, 0.82],
    "latency_ms": 450,
    "validation": {
      "is_valid": true,
      "is_ecommerce_related": true,
      "is_safe": true
    }
  }
}
```

**Status Codes**:
- 200: Success
- 400: Invalid query
- 500: Service error

#### POST /v1/evaluate_rag
Evaluate RAG system performance.

**Request Body**:
```json
{
  "test_cases": [
    {
      "question": "What are the cheapest products?",
      "expected_answer": "Products with lowest prices",
      "relevant_products": ["product-id-1", "product-id-2"]
    }
  ]
}
```

**Response**:
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

---

## Error Responses

All errors follow this format:

```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "request_id": "uuid"
}
```

**Common Status Codes**:
- 400: Bad Request (validation error)
- 429: Rate Limit Exceeded
- 500: Internal Server Error
- 503: Service Unavailable

## Rate Limiting

- Default: 60 requests per minute per IP
- Configurable via `RATE_LIMIT_PER_MINUTE` environment variable
- Headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Request ID

All responses include `X-Request-ID` header for tracing.

## Interactive Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Examples

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Predict discount
curl -X POST http://localhost:8000/v1/predict_discount \
  -H "Content-Type: application/json" \
  -d '{
    "price": 100.0,
    "category": "Electronics"
  }'

# Answer question
curl -X POST http://localhost:8000/v1/answer_question \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the best products?",
    "top_k": 5
  }'
```

### Python Example

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# Predict discount
response = client.post("/v1/predict_discount", json={
    "price": 100.0,
    "category": "Electronics",
    "rating": 4.5
})
print(response.json())

# Answer question
response = client.post("/v1/answer_question", json={
    "question": "What are the cheapest products?",
    "top_k": 5
})
print(response.json())
```



