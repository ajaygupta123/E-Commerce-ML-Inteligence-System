# Architecture Decision Records

This document outlines all major architectural decisions with justifications.

## 1. Database Selection: PostgreSQL over MySQL/MariaDB/SQLite

**Decision**: PostgreSQL 17 Alpine

**Alternatives Considered**:
- MySQL: Weaker query optimizer, less feature-rich
- MariaDB: Good but PostgreSQL has better analytics support
- SQLite: Single-user, not production-ready
- CockroachDB: Over-engineering, licensing issues

**Justification**:
- 1.6x faster than MySQL on complex queries (benchmarks)
- Superior JSON support for flexible product attributes
- Materialized views for caching aggregations
- Row-level security out of the box
- Industry standard for ML/analytics workloads
- Used by Instagram, Notion, Stripe at scale
- Alpine image reduces image size by 60%

## 2. Vector Database: Qdrant over pgvector

**Decision**: Qdrant

**Alternatives Considered**:
- pgvector: Part of PostgreSQL

**Justification**:
- 15x better throughput on filtered queries
- Purpose-built HNSW with optimized filtering
- pgvector uses full-scan on filters (O(n))
- Native horizontal scaling
- Cleaner separation of concerns
- 18% better accuracy in benchmarks
- Better memory efficiency for large-scale deployments

## 3. LLM Strategy: Adaptation (RAG) over Fine-tuning

**Decision**: RAG + Prompt Engineering

**Why NOT Fine-tuning**:
- E-commerce catalogs change daily; fine-tuning requires retraining
- Fine-tuned models hallucinate; RAG grounds in actual data
- Fine-tuning small models (1-3B) often degrades capabilities
- Industry standard: Amazon Rufus, Shopify Sidekick use RAG
- Cost: Fine-tuning requires GPU clusters; RAG uses inference-only

**Adaptation Techniques Implemented**:
- Retrieval Augmentation (Qdrant)
- System Prompt Engineering
- Few-shot Examples
- Output Guardrails

**If Fine-tuning Were Required**:
- Model: Llama 3.2 3B
- Method: QLoRA (4-bit + LoRA adapters)
- Compute: Single GPU, ~2-4 hours
- Cost: ~$50-100 per fine-tune run

## 4. ML Model: CatBoost over LightGBM/XGBoost

**Decision**: CatBoost (with LightGBM baseline)

**Justification**:
- Better handling of categorical features (native)
- Superior performance on tabular data
- Built-in SHAP support
- Less hyperparameter tuning required
- Better generalization on small datasets
- [Actual comparison metrics from training will be documented in MODEL_CARD.md]

**LightGBM Baseline**:
- Trained as baseline for comparison
- Demonstrates ML maturity and evaluation rigor
- Provides performance benchmark

## 5. Self-Hosted LLM over API

**Decision**: Ollama (Llama 3.2 3B)

**Why NOT Groq/OpenRouter API**:
- More control over optimization
- No rate limits in demo
- More interview talking points
- Data privacy (no external calls)
- Cost: Free vs. $0.10-0.50 per 1K tokens
- Latency: Local inference vs. network round-trip

**Optimizations Applied**:
- Q4_K_M quantization (4x memory reduction)
- Context window: 2048 (speed over context)
- num_gpu=99 (full GPU offload)
- num_thread=4 (CPU optimization)

## 6. Cache Strategy: In-Memory with Redis Abstraction

**Decision**: In-memory cache with abstracted backend

**Justification**:
- Simple for MVP/demo
- Easy swap to Redis for production
- No external dependencies for local dev
- TTL-based expiration
- Production swap: Change CacheBackend implementation

**Production Considerations**:
- Redis for distributed caching
- Cache warming strategies
- Cache invalidation policies

## 7. Model Storage: Local Filesystem with S3 Abstraction

**Decision**: Local filesystem with abstracted loader

**Justification**:
- Simple for MVP
- Easy swap to S3/MinIO
- ModelLoader abstraction allows versioning
- Production: S3 for model versioning, A/B testing

**Production Enhancements**:
- Model versioning (v1, v2, etc.)
- A/B testing support
- Rollback capabilities
- Distributed access

## 8. API Framework: FastAPI

**Decision**: FastAPI

**Alternatives Considered**:
- Flask: No async, slower
- Django: Over-engineered for API-only
- Express.js: Wrong language

**Justification**:
- Native async/await support
- Auto-generated OpenAPI docs
- Type hints with Pydantic
- High performance (comparable to Node.js)
- Modern Python best practices

## 9. Containerization: Multi-Stage Docker Builds

**Decision**: Multi-stage builds for optimization

**Justification**:
- Final image size: ~200MB (vs. 800MB+ single-stage)
- Faster deployments
- Better security (minimal runtime)
- Industry best practice

## 10. Observability: Prometheus + Grafana

**Decision**: Prometheus metrics + Grafana dashboards

**Justification**:
- Industry standard
- Easy integration with FastAPI
- Rich ecosystem
- Production-ready monitoring

## 11. Testing Strategy

**Decision**: pytest + Locust

**Justification**:
- pytest: Python standard, async support
- Unit tests: Fast feedback
- Integration tests: End-to-end validation
- Load tests: Performance validation
- Coverage: 80%+ target

## 12. Feature Engineering Pipeline

**Decision**: Reusable FeatureEngineer class

**Justification**:
- Consistent preprocessing
- Saves transformers for inference
- Handles unseen categories
- Easy to extend

## 13. Error Handling

**Decision**: Custom exception hierarchy

**Justification**:
- Clear error types
- Better debugging
- Consistent API responses
- Production logging

## 14. Rate Limiting

**Decision**: In-memory rate limiter (Redis-ready)

**Justification**:
- Simple for MVP
- Easy swap to Redis
- Per-IP limiting
- Configurable limits

## 15. Security Considerations

**Decisions**:
- Input validation (Pydantic)
- Guardrails service
- Rate limiting
- CORS configuration
- No secrets in code (.env)

**Production Enhancements**:
- JWT authentication
- API keys
- OAuth2
- Request signing
- DDoS protection




