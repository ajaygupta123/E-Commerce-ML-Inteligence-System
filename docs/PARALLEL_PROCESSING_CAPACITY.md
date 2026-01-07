# Parallel Processing Capacity Analysis

## Current Configuration

### 1. API Server (FastAPI/Uvicorn)
- **Workers**: 1 (single process)
- **Concurrency Model**: Async (event loop)
- **Theoretical Capacity**: 1000+ concurrent requests (async I/O bound)
- **Bottleneck**: Not the API server itself, but downstream services

**Location**: `docker/api.Dockerfile` line 39
```bash
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. LLM Service (Ollama) - **PRIMARY BOTTLENECK**
- **Semaphore Limit**: 5 concurrent requests (configurable)
- **Ollama Config**: `OLLAMA_NUM_PARALLEL=2` (in docker-compose)
- **HTTP Client**: 10 max connections, 5 keepalive
- **Memory Limit**: 4GB
- **Current Capacity**: ~5-10 requests/second (depending on response time)

**Location**: 
- `src/services/llm_service.py` line 31: `asyncio.Semaphore(5)`
- `docker-compose.yml` line 76: `OLLAMA_NUM_PARALLEL=2`

### 3. Database (PostgreSQL)
- **Pool Size**: 50 base connections
- **Max Overflow**: 100 additional connections
- **Total Capacity**: 150 concurrent database connections
- **Current Capacity**: Can handle 150+ concurrent requests

**Location**: `src/db/postgres.py` lines 16-17

### 4. Vector Database (Qdrant)
- **No explicit limits configured**
- **Capacity**: Very high (handles thousands of concurrent searches)
- **Not a bottleneck** for current load

### 5. Rate Limiting
- **Default**: 60 requests/minute per IP
- **Status**: Can be disabled for load testing
- **Impact**: Limits throughput when enabled

## Current Maximum Parallel Processing

### For Prediction Endpoints (`/v1/predict_discount`)
- **Bottleneck**: Database connections (150 max)
- **Theoretical Max**: ~150 concurrent requests
- **Practical Max**: ~100-120 concurrent (accounting for overhead)
- **Throughput**: ~2000-3000 requests/minute

### For RAG Endpoints (`/v1/answer_question`)
- **Bottleneck**: Ollama LLM service
- **Current Limit**: 5 concurrent LLM requests (semaphore)
- **Ollama Limit**: 2 parallel (OLLAMA_NUM_PARALLEL=2)
- **Theoretical Max**: ~5-10 requests/second
- **Practical Max**: ~3-5 requests/second (accounting for latency)
- **Throughput**: ~180-300 requests/minute

**Note**: Additional requests wait in queue (non-blocking)

## Bottleneck Analysis

### Critical Bottlenecks (in order)

1. **Ollama LLM Service** ⚠️ **PRIMARY**
   - **Limit**: 5 concurrent (semaphore) + 2 parallel (Ollama config)
   - **Impact**: High - causes 500 errors under load
   - **Solution**: Increase semaphore, scale Ollama horizontally

2. **Database Connection Pool**
   - **Limit**: 150 total connections
   - **Impact**: Medium - may limit prediction endpoint
   - **Solution**: Increase pool size if needed

3. **HTTP Client Connections**
   - **Limit**: 10 max connections to Ollama
   - **Impact**: Low - semaphore already limits to 5
   - **Solution**: Increase if semaphore is increased

4. **API Server Workers**
   - **Limit**: 1 worker (single process)
   - **Impact**: Low - async handles concurrency well
   - **Solution**: Add workers for CPU-bound operations

## Scaling Options

### Option 1: Increase LLM Semaphore (Quick Fix)

**Current**: 5 concurrent requests
**Recommended**: 10-15 concurrent requests

**How to change**:
```python
# In src/services/llm_service.py
def __init__(self, max_concurrent_requests: int = 10):  # Changed from 5
    self.semaphore = asyncio.Semaphore(max_concurrent_requests)
```

**Trade-offs**:
- ✅ More throughput
- ❌ May overwhelm Ollama if too high
- ❌ Higher memory usage

**Expected improvement**: 2x throughput (5 → 10 req/s)

### Option 2: Increase Ollama Parallel Processing

**Current**: `OLLAMA_NUM_PARALLEL=2`
**Recommended**: `OLLAMA_NUM_PARALLEL=4-8` (depending on CPU/memory)

**How to change**:
```yaml
# In docker-compose.yml
ollama:
  environment:
    - OLLAMA_NUM_PARALLEL=4  # Changed from 2
  deploy:
    resources:
      limits:
        memory: 8G  # Increase if needed
```

**Trade-offs**:
- ✅ Better utilization of resources
- ❌ Higher memory/CPU usage
- ❌ May need more memory allocation

**Expected improvement**: 2-4x throughput

### Option 3: Horizontal Scaling - Multiple Ollama Instances

**Approach**: Run multiple Ollama containers with load balancing

**Implementation**:
```yaml
# docker-compose.yml
ollama-1:
  image: ollama/ollama:latest
  # ... config ...
ollama-2:
  image: ollama/ollama:latest
  # ... config ...
ollama-3:
  image: ollama/ollama:latest
  # ... config ...
```

**Load balancer**: Use nginx or similar to distribute requests

**Expected improvement**: Linear scaling (3 instances = 3x capacity)

### Option 4: Increase Database Pool Size

**Current**: 50 base + 100 overflow = 150 total
**Recommended**: 100 base + 200 overflow = 300 total (if needed)

**How to change**:
```python
# In src/db/postgres.py
pool_size=100,  # Changed from 50
max_overflow=200,  # Changed from 100
```

**Trade-offs**:
- ✅ More concurrent database operations
- ❌ Higher database resource usage
- ❌ May hit PostgreSQL max_connections limit

### Option 5: Add API Workers (For CPU-bound tasks)

**Current**: 1 worker
**Recommended**: 2-4 workers (for CPU-bound operations)

**How to change**:
```dockerfile
# In docker/api.Dockerfile
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Trade-offs**:
- ✅ Better for CPU-bound tasks (embeddings, ML inference)
- ❌ More memory usage
- ❌ Shared state issues (caching, singletons)

**Note**: Not recommended for async I/O bound workloads (current setup)

### Option 6: Increase HTTP Client Connections

**Current**: 10 max connections, 5 keepalive
**Recommended**: 20 max connections, 10 keepalive (if semaphore increased)

**How to change**:
```python
# In src/services/llm_service.py
self.client = httpx.AsyncClient(
    timeout=180.0,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
)
```

## Recommended Scaling Strategy

### Phase 1: Quick Wins (Low Risk)
1. ✅ Increase LLM semaphore: 5 → 10
2. ✅ Increase Ollama parallel: 2 → 4
3. ✅ Increase Ollama memory: 4GB → 8GB

**Expected**: 2-3x improvement in RAG throughput

### Phase 2: Medium-term (Moderate Risk)
1. Add 2-3 Ollama instances with load balancing
2. Increase database pool if needed
3. Monitor and tune based on metrics

**Expected**: 5-10x improvement in RAG throughput

### Phase 3: Long-term (Higher Complexity)
1. Implement Ollama cluster with proper load balancing
2. Consider using faster LLM inference servers (vLLM, TensorRT-LLM)
3. Implement request prioritization and queuing strategies
4. Add caching layers (Redis) for better performance

**Expected**: 10-50x improvement depending on infrastructure

## Capacity Summary

| Component | Current Limit | Max Theoretical | Bottleneck? |
|-----------|--------------|-----------------|-------------|
| API Server | 1000+ async | 10,000+ | ❌ No |
| LLM Service | 5 concurrent | 10-20 (with scaling) | ✅ **Yes** |
| Database | 150 connections | 500+ | ⚠️ Maybe |
| Qdrant | Unlimited | 10,000+ | ❌ No |
| HTTP Client | 10 connections | 50+ | ⚠️ Minor |

## Monitoring Recommendations

Track these metrics to identify bottlenecks:
1. **LLM Request Queue Length**: How many requests are waiting
2. **Ollama Response Time**: P50, P95, P99 latencies
3. **Database Connection Pool Usage**: Active vs. available
4. **Error Rates**: 500 errors by endpoint
5. **Throughput**: Requests/second by endpoint

## Conclusion

**Current Maximum Parallel Processing**:
- **Prediction Endpoints**: ~100-150 concurrent requests
- **RAG Endpoints**: ~5 concurrent requests (primary bottleneck)

**Quick Improvement**: Increase LLM semaphore to 10 and Ollama parallel to 4
- **Expected**: 2-3x improvement (5 → 10-15 req/s)

**Best Long-term Solution**: Horizontal scaling with multiple Ollama instances
- **Expected**: Linear scaling (3 instances = 3x capacity)


