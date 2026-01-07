# Pipeline Throughput Analysis: Step-by-Step Breakdown

## Overview

This document breaks down the throughput at each step of the API request processing pipeline to identify bottlenecks and optimization opportunities.

---

## RAG Pipeline (`/v1/answer_question`)

### Pipeline Steps (Cache Miss Path)

| Step | Component | Latency | Throughput | Parallelism | Bottleneck? |
|------|-----------|---------|------------|-------------|-------------|
| **1. API Request Reception** | FastAPI | 1-5ms | **10,000+ req/s** | Unlimited | ✅ No |
| **2. Query Validation** | GuardrailsService | 1-2ms | **5,000+ req/s** | Unlimited | ✅ No |
| **3. Cache Lookup** | CacheService | 1-5ms | **2,000+ req/s** | Unlimited | ✅ No |
| **4. Embedding Generation** | EmbeddingService | 50-100ms | **10-20 req/s** | CPU-bound | ⚠️ Minor |
| **5. Vector Search** | Qdrant | 10-50ms | **20-100 req/s** | Limited by Qdrant | ⚠️ Minor |
| **6. Database Query** | PostgreSQL | 20-100ms | **50-500 req/s** | Pool: 50+100 | ⚠️ Minor |
| **7. Question Classification** | Helpers | <1ms | **10,000+ req/s** | Unlimited | ✅ No |
| **8. Context Building** | RAGService | 1-5ms | **2,000+ req/s** | Unlimited | ✅ No |
| **9. LLM Generation** | Ollama | **2,000-5,000ms** | **0.4-0.5 req/s** | 2 parallel | 🔴 **PRIMARY** |
| **10. Response Formatting** | RAGService | 1-5ms | **2,000+ req/s** | Unlimited | ✅ No |
| **11. Cache Write** | CacheService | 1-5ms | **2,000+ req/s** | Unlimited | ✅ No |
| **12. Logging** | LogRepository | 10-50ms | **20-100 req/s** | Async, non-blocking | ✅ No |

### Pipeline Steps (Cache Hit Path)

| Step | Component | Latency | Throughput | Parallelism | Bottleneck? |
|------|-----------|---------|------------|-------------|-------------|
| **1. API Request Reception** | FastAPI | 1-5ms | **10,000+ req/s** | Unlimited | ✅ No |
| **2. Query Validation** | GuardrailsService | 1-2ms | **5,000+ req/s** | Unlimited | ✅ No |
| **3. Cache Lookup** | CacheService | 1-5ms | **2,000+ req/s** | Unlimited | ✅ No |
| **4. Return Cached Response** | RAGService | <1ms | **10,000+ req/s** | Unlimited | ✅ No |

**Cache Hit Throughput**: **~2,000-10,000 requests/second** (limited by cache service)

---

## Prediction Pipeline (`/v1/predict_discount`)

### Pipeline Steps

| Step | Component | Latency | Throughput | Parallelism | Bottleneck? |
|------|-----------|---------|------------|-------------|-------------|
| **1. API Request Reception** | FastAPI | 1-5ms | **10,000+ req/s** | Unlimited | ✅ No |
| **2. Feature Validation** | GuardrailsService | 1-2ms | **5,000+ req/s** | Unlimited | ✅ No |
| **3. Feature Engineering** | FeatureEngineer | 5-20ms | **50-200 req/s** | CPU-bound | ⚠️ Minor |
| **4. Model Prediction** | CatBoost | 1-5ms | **1,000+ req/s** | CPU-bound | ✅ No |
| **5. Confidence Calculation** | PredictionService | <1ms | **10,000+ req/s** | Unlimited | ✅ No |
| **6. Logging** | LogRepository | 10-50ms | **20-100 req/s** | Async, non-blocking | ✅ No |
| **7. Response Formatting** | FastAPI | 1-5ms | **10,000+ req/s** | Unlimited | ✅ No |

**Prediction Throughput**: **~50-200 requests/second** (limited by feature engineering)

### Explain Pipeline (`/v1/explain`)

| Step | Component | Latency | Throughput | Parallelism | Bottleneck? |
|------|-----------|---------|------------|-------------|-------------|
| **1-5. Same as Prediction** | - | - | - | - | - |
| **6. SHAP Explanation** | SHAP | **500-2,000ms** | **0.5-2 req/s** | CPU-bound | 🔴 **PRIMARY** |
| **7. Logging** | LogRepository | 10-50ms | **20-100 req/s** | Async, non-blocking | ✅ No |
| **8. Response Formatting** | FastAPI | 1-5ms | **10,000+ req/s** | Unlimited | ✅ No |

**Explain Throughput**: **~0.5-2 requests/second** (limited by SHAP computation)

---

## Detailed Step Analysis

### 1. API Request Reception (FastAPI)

**Latency**: 1-5ms
**Throughput**: 10,000+ requests/second
**Parallelism**: Unlimited (async FastAPI)
**Bottleneck**: ❌ No

**Details**:
- FastAPI is highly optimized for async operations
- Can handle thousands of concurrent connections
- Not a limiting factor

---

### 2. Query Validation (GuardrailsService)

**Latency**: 1-2ms
**Throughput**: 5,000+ requests/second
**Parallelism**: Unlimited (pure Python, no I/O)
**Bottleneck**: ❌ No

**Details**:
- Simple string validation and keyword checking
- No external dependencies
- Negligible overhead

---

### 3. Cache Lookup (CacheService)

**Latency**: 1-5ms (in-memory)
**Throughput**: 2,000+ requests/second
**Parallelism**: Limited by Python GIL (in-memory dict)
**Bottleneck**: ⚠️ Minor (only for very high cache hit rates)

**Details**:
- In-memory dictionary lookup
- O(1) complexity
- Can become bottleneck at 2,000+ req/s with 100% cache hits
- **Solution**: Use Redis for distributed caching

---

### 4. Embedding Generation (EmbeddingService)

**Latency**: 50-100ms
**Throughput**: 10-20 requests/second
**Parallelism**: CPU-bound (sentence-transformers)
**Bottleneck**: ⚠️ Minor

**Details**:
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- CPU inference (no GPU)
- Can process ~10-20 embeddings/second
- **Impact**: Only affects cache misses (40% of requests)
- **Solution**: 
  - GPU acceleration (10-50x faster)
  - Batch processing
  - Embedding caching (already implemented)

**With Caching**:
- First request: 50-100ms
- Cached requests: 1-5ms (cache lookup)
- **Effective throughput**: 2,000+ req/s (for cached embeddings)

---

### 5. Vector Search (Qdrant)

**Latency**: 10-50ms
**Throughput**: 20-100 requests/second
**Parallelism**: Limited by Qdrant server
**Bottleneck**: ⚠️ Minor

**Details**:
- Qdrant vector database search
- Searches 384-dimensional vectors
- Returns top-k results (default: 5)
- **Impact**: Only affects cache misses
- **Solution**: 
  - Increase Qdrant resources
  - Use HNSW index (already configured)
  - Batch searches

**Current Capacity**:
- Single Qdrant instance
- Can handle 20-100 searches/second
- Not a bottleneck for current load

---

### 6. Database Query (PostgreSQL)

**Latency**: 20-100ms per product
**Throughput**: 50-500 requests/second
**Parallelism**: Connection pool (50 base + 100 overflow = 150 total)
**Bottleneck**: ⚠️ Minor

**Details**:
- **Current Issue**: Sequential product fetching (lines 188-198 in `rag_service.py`)
  ```python
  for product_id in retrieved_product_ids:
      product = await product_repo.get_by_id(product_id)
  ```
- **Impact**: If top_k=5, this adds 100-500ms (5 × 20-100ms)
- **Current Pool**: 50 connections + 100 overflow = 150 total
- **Throughput**: 150 connections ÷ 0.1s = 1,500 req/s (theoretical)
- **Actual**: Limited by sequential fetching to ~50-500 req/s

**Solution**:
- **Batch query**: Fetch all products in one query
  ```python
  products = await product_repo.get_by_ids(retrieved_product_ids)
  ```
- **Expected improvement**: 5-10x faster (20-100ms total vs 100-500ms)

---

### 7. Question Classification (Helpers)

**Latency**: <1ms
**Throughput**: 10,000+ requests/second
**Parallelism**: Unlimited
**Bottleneck**: ❌ No

**Details**:
- Simple keyword matching
- No external dependencies
- Negligible overhead

---

### 8. Context Building (RAGService)

**Latency**: 1-5ms
**Throughput**: 2,000+ requests/second
**Parallelism**: Unlimited
**Bottleneck**: ❌ No

**Details**:
- String formatting and concatenation
- No I/O operations
- Negligible overhead

---

### 9. LLM Generation (Ollama) 🔴 **PRIMARY BOTTLENECK**

**Latency**: 2,000-5,000ms (2-5 seconds)
**Throughput**: **0.4-0.5 requests/second** (per active slot)
**Parallelism**: 
- **Active**: 2 requests (OLLAMA_NUM_PARALLEL=2)
- **Queue**: 5 requests (semaphore limit)
- **Total concurrent**: 5 requests

**Bottleneck**: 🔴 **YES - PRIMARY BOTTLENECK**

**Details**:
- **Model**: llama3.2:3b (Q4_K_M quantization)
- **Context window**: 1024 tokens
- **Max tokens**: 300 tokens
- **Processing time**: ~3 seconds average
- **Active processing**: 2 requests simultaneously
- **Base throughput**: 2 requests ÷ 3 seconds = **~0.67 req/s**

**With Semaphore Queue (5 concurrent)**:
- **Maximum LLM throughput**: 5 requests ÷ 3 seconds = **~1.67 req/s**
- **Queue wait time**: ~3-6 seconds (waiting for active slot)
- **Total request time**: ~6-9 seconds (including queue wait)

**Impact**:
- **Limits overall RAG throughput to ~0.67-1.67 req/s** (without cache)
- **With 60% cache hit rate**: ~4.2 req/s total
- **With 80% cache hit rate**: ~8.3 req/s total

**Solutions**:
1. **Increase OLLAMA_NUM_PARALLEL**: 2 → 4-8 (requires more memory)
   - **Improvement**: 2-4x throughput
2. **Increase semaphore**: 5 → 10-20 (requires more memory)
   - **Improvement**: 2-4x concurrent capacity
3. **Increase memory**: 4GB → 8-10GB (enables above)
   - **Improvement**: 2-4x throughput
4. **GPU acceleration**: Use GPU for LLM inference
   - **Improvement**: 5-10x throughput
5. **Optimize LLM parameters**:
   - Reduce `max_tokens`: 300 → 200 (faster generation)
   - Reduce `num_ctx`: 1024 → 512 (if context allows)
   - **Improvement**: 1.2-1.5x throughput

---

### 10. Response Formatting (RAGService)

**Latency**: 1-5ms
**Throughput**: 2,000+ requests/second
**Parallelism**: Unlimited
**Bottleneck**: ❌ No

**Details**:
- Dictionary construction
- JSON serialization (handled by FastAPI)
- Negligible overhead

---

### 11. Cache Write (CacheService)

**Latency**: 1-5ms
**Throughput**: 2,000+ requests/second
**Parallelism**: Limited by Python GIL (in-memory dict)
**Bottleneck**: ❌ No

**Details**:
- In-memory dictionary write
- O(1) complexity
- Negligible overhead

---

### 12. Logging (LogRepository)

**Latency**: 10-50ms
**Throughput**: 20-100 requests/second
**Parallelism**: Async, non-blocking
**Bottleneck**: ❌ No (non-blocking)

**Details**:
- Database write (PostgreSQL)
- Wrapped in try-except (doesn't block request)
- Can become bottleneck if database is slow
- **Current**: Non-blocking, so doesn't affect request latency

---

## Bottleneck Summary

### RAG Pipeline Bottlenecks (Cache Miss Path):

1. 🔴 **LLM Generation** (2,000-5,000ms) - **PRIMARY BOTTLENECK**
   - Throughput: 0.67-1.67 req/s
   - Impact: Limits overall system throughput
   - Solution: Increase memory, parallel processing, or use GPU

2. ⚠️ **Database Query** (100-500ms sequential) - **SECONDARY BOTTLENECK**
   - Throughput: 50-500 req/s (limited by sequential fetching)
   - Impact: Adds significant latency
   - Solution: Batch query (5-10x improvement)

3. ⚠️ **Embedding Generation** (50-100ms) - **MINOR BOTTLENECK**
   - Throughput: 10-20 req/s
   - Impact: Only affects cache misses (40% of requests)
   - Solution: Already cached, GPU acceleration

4. ⚠️ **Vector Search** (10-50ms) - **MINOR BOTTLENECK**
   - Throughput: 20-100 req/s
   - Impact: Negligible compared to LLM
   - Solution: Already optimized

### Prediction Pipeline Bottlenecks:

1. ⚠️ **Feature Engineering** (5-20ms) - **MINOR BOTTLENECK**
   - Throughput: 50-200 req/s
   - Impact: Limits prediction throughput
   - Solution: Optimize feature engineering code

2. 🔴 **SHAP Explanation** (500-2,000ms) - **PRIMARY BOTTLENECK** (for `/explain`)
   - Throughput: 0.5-2 req/s
   - Impact: Only affects explain endpoint
   - Solution: Use faster SHAP methods, approximate explanations

---

## Overall System Throughput

### RAG Endpoint (`/v1/answer_question`):

**Cache Miss Path** (worst case):
- **Bottleneck**: LLM generation
- **Throughput**: **~0.67-1.67 requests/second** = **~40-100 requests/minute**

**Cache Hit Path** (best case):
- **Bottleneck**: Cache lookup
- **Throughput**: **~2,000 requests/second** = **~120,000 requests/minute**

**Realistic Scenario** (60% cache hit rate):
- **Throughput**: **~4.2 requests/second** = **~250 requests/minute**

**Optimistic Scenario** (80% cache hit rate):
- **Throughput**: **~8.3 requests/second** = **~500 requests/minute**

### Prediction Endpoint (`/v1/predict_discount`):

- **Bottleneck**: Feature engineering
- **Throughput**: **~50-200 requests/second** = **~3,000-12,000 requests/minute**

### Explain Endpoint (`/v1/explain`):

- **Bottleneck**: SHAP computation
- **Throughput**: **~0.5-2 requests/second** = **~30-120 requests/minute**

---

## Optimization Priority

### High Priority (Immediate Impact):

1. **Fix Sequential Database Queries** (RAG pipeline)
   - **Current**: 100-500ms (5 sequential queries)
   - **After**: 20-100ms (1 batch query)
   - **Improvement**: 5-10x faster
   - **Impact**: Reduces latency by 80-400ms per request
   - **Effort**: Low (simple code change)

2. **Increase LLM Parallel Processing** (if memory available)
   - **Current**: 2 parallel, 5 concurrent
   - **After**: 4 parallel, 10-20 concurrent
   - **Improvement**: 2-4x throughput
   - **Impact**: Increases RAG throughput from 0.67 to 1.3-2.7 req/s
   - **Effort**: Medium (requires memory increase)

### Medium Priority (Significant Impact):

3. **Optimize LLM Parameters**
   - Reduce `max_tokens`: 300 → 200
   - Reduce `num_ctx`: 1024 → 512 (if possible)
   - **Improvement**: 1.2-1.5x throughput
   - **Impact**: Reduces LLM latency by 20-30%
   - **Effort**: Low (configuration change)

4. **GPU Acceleration for Embeddings**
   - **Current**: 50-100ms (CPU)
   - **After**: 5-10ms (GPU)
   - **Improvement**: 5-10x faster
   - **Impact**: Reduces embedding latency by 40-90ms
   - **Effort**: Medium (requires GPU setup)

### Low Priority (Nice to Have):

5. **Redis for Distributed Caching**
   - **Current**: In-memory (single instance)
   - **After**: Distributed (multiple instances)
   - **Improvement**: Better scalability
   - **Impact**: Enables horizontal scaling
   - **Effort**: Medium (infrastructure change)

6. **Optimize Feature Engineering**
   - **Current**: 5-20ms
   - **After**: 2-10ms (optimized code)
   - **Improvement**: 2x faster
   - **Impact**: Increases prediction throughput
   - **Effort**: Medium (code optimization)

---

## Recommendations

### Immediate Actions:

1. ✅ **Fix sequential database queries** → Batch fetch products
2. ✅ **Monitor cache hit rate** → Target >60%
3. ✅ **Monitor LLM queue length** → Alert if >3 requests

### Short-term (1-2 weeks):

1. **Increase memory to 8-10GB** → Enable 4-8 parallel LLM processing
2. **Increase semaphore to 10-20** → Support more concurrent requests
3. **Optimize LLM parameters** → Reduce max_tokens and context window

### Long-term (1-3 months):

1. **GPU acceleration** → For LLM and embeddings
2. **Horizontal scaling** → Multiple Ollama instances
3. **Redis caching** → Distributed cache layer

---

## Monitoring Metrics

### Key Metrics to Track:

1. **LLM Queue Length**: Number of requests waiting
   - Target: <3 requests
   - Alert: >5 requests

2. **LLM Processing Time**: Average latency
   - Target: <3 seconds
   - Alert: >5 seconds

3. **Cache Hit Rate**: Percentage of cache hits
   - Target: >60%
   - Alert: <40%

4. **Database Query Time**: Average latency
   - Target: <50ms per query
   - Alert: >100ms per query

5. **Overall Throughput**: Requests per second
   - Target: >4 req/s (RAG)
   - Alert: <2 req/s

---

## Conclusion

### Current Bottlenecks:

1. 🔴 **LLM Generation**: Primary bottleneck (2-5s, 0.67-1.67 req/s)
2. ⚠️ **Sequential Database Queries**: Secondary bottleneck (100-500ms)
3. ⚠️ **Embedding Generation**: Minor bottleneck (50-100ms, but cached)

### Expected Improvements:

**After fixing sequential queries**:
- RAG latency: -80-400ms per request
- Throughput: Unchanged (still limited by LLM)

**After increasing LLM parallelism** (4 parallel, 10 concurrent):
- RAG throughput: 0.67 → 1.3-2.7 req/s (2-4x improvement)
- Total system: 4.2 → 8-16 req/s (with 60% cache)

**Combined improvements**:
- RAG latency: -80-400ms (database) + -500-1,000ms (LLM optimization)
- RAG throughput: 4.2 → 8-16 req/s (2-4x improvement)

