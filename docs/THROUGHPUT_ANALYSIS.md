# Throughput Analysis: Current Configuration

## Current System Configuration

### Hardware/Resource Limits:
- **Ollama Memory**: 4GB
- **OLLAMA_NUM_PARALLEL**: 2 (2 requests process simultaneously)
- **Semaphore Limit**: 5 (max 5 concurrent requests to Ollama)
- **Database Pool**: 50 connections, 100 max overflow
- **Rate Limiting**: 60 requests/minute (if enabled)

### LLM Configuration:
- **Model**: llama3.2:3b (Q4_K_M quantization)
- **Context Window**: 1024 tokens
- **Max Tokens**: 300 tokens
- **Temperature**: 0.5
- **Top-k**: 40, Top-p: 0.9

## Request Processing Pipeline

### Typical Request Flow:
1. **API receives request** → ~1-5ms
2. **Query validation** → ~1ms
3. **Embedding generation** (if not cached) → ~50-100ms
4. **Vector search (Qdrant)** → ~10-50ms
5. **Database query (PostgreSQL)** → ~20-100ms
6. **LLM generation** → **2,000-5,000ms** ⚠️ **BOTTLENECK**
7. **Response formatting** → ~5-10ms

**Total Time**: ~2.1-5.3 seconds per request (without cache)

### With Cache Hit:
1. **API receives request** → ~1-5ms
2. **Cache lookup** → ~1-5ms
3. **Return cached response** → ~1ms

**Total Time**: ~3-11ms per request (with cache)

## Throughput Calculations

### Scenario 1: All Requests Hit LLM (Worst Case - No Cache)

**LLM Processing Capacity**:
- **Active processing**: 2 requests simultaneously (OLLAMA_NUM_PARALLEL=2)
- **Average LLM time**: ~3 seconds per request
- **Throughput**: 2 requests / 3 seconds = **~0.67 requests/second**

**With Semaphore Queue**:
- **Max concurrent**: 5 requests
- **Processing pattern**: 2 active, 3 queued
- **Queue wait time**: ~3-6 seconds (waiting for active slot)
- **Total request time**: ~6-9 seconds (including queue wait)

**Actual Throughput**: **~0.67 requests/second** = **~40 requests/minute**

**Bottleneck**: LLM processing speed (2 parallel, ~3s each)

### Scenario 2: Mixed Load (50% Cache Hit Rate)

**Cache Hits** (50%):
- Processing time: ~5ms
- Throughput: **~100 requests/second** (limited by API, not LLM)

**Cache Misses** (50%):
- Processing time: ~3-5 seconds
- Throughput: **~0.67 requests/second** (LLM bottleneck)

**Combined Throughput**:
- Cache hits: 50% × 100 req/s = 50 req/s
- Cache misses: 50% × 0.67 req/s = 0.34 req/s
- **Total**: **~50 requests/second** = **~3,000 requests/minute**

**Note**: This assumes API can handle 100 req/s for cached requests. Actual may be lower.

### Scenario 3: High Cache Hit Rate (80% Cache Hits)

**Cache Hits** (80%):
- Throughput: **~100 requests/second**

**Cache Misses** (20%):
- Throughput: **~0.67 requests/second**

**Combined Throughput**:
- Cache hits: 80% × 100 req/s = 80 req/s
- Cache misses: 20% × 0.67 req/s = 0.13 req/s
- **Total**: **~80 requests/second** = **~4,800 requests/minute**

### Scenario 4: All Cache Misses (Worst Case - New Queries)

**Throughput**: **~0.67 requests/second** = **~40 requests/minute**

**Request Timeline**:
```
Time 0s: Request 1, 2 arrive → Start processing (2 active)
Time 3s: Request 1, 2 complete → Request 3, 4 start (from queue)
Time 6s: Request 3, 4 complete → Request 5 starts (from queue)
Time 9s: Request 5 completes
```

**Average response time**: ~6-9 seconds (including queue wait)

## Realistic Throughput Estimates

### Conservative Estimate (Realistic Production):

**Assumptions**:
- 60% cache hit rate (common for e-commerce queries)
- LLM processing: 3 seconds average
- API overhead: 100-200ms per request

**Calculation**:
- **Cache hits** (60%): ~50-100 req/s (limited by API capacity)
- **Cache misses** (40%): ~0.67 req/s (LLM bottleneck)
- **Combined**: **~50-100 requests/second** = **~3,000-6,000 requests/minute**

**But wait!** The semaphore limit of 5 means:
- Only 5 requests can be in the LLM queue at once
- If 40% miss cache, and we get 100 req/s total:
  - 40 req/s need LLM = 40 × 3s = 120 requests in flight
  - But semaphore only allows 5!
  - **Result**: Requests will be rejected or timeout

**Realistic Throughput with Semaphore=5**:
- Max LLM capacity: 5 concurrent requests
- Average LLM time: 3 seconds
- **LLM throughput**: 5 / 3s = **~1.67 requests/second**
- **Cache hits**: Can be much higher, but limited by overall system

**If 60% cache hit rate**:
- LLM handles: 1.67 req/s
- This represents 40% of total (cache misses)
- **Total throughput**: 1.67 / 0.4 = **~4.2 requests/second** = **~250 requests/minute**

### Optimistic Estimate (High Cache Hit Rate):

**Assumptions**:
- 80% cache hit rate
- LLM processing: 3 seconds average

**Calculation**:
- **Cache misses** (20%): Limited by semaphore=5
- **LLM throughput**: ~1.67 req/s (5 concurrent / 3s)
- **Total throughput**: 1.67 / 0.2 = **~8.3 requests/second** = **~500 requests/minute**

### Pessimistic Estimate (Low Cache Hit Rate):

**Assumptions**:
- 20% cache hit rate
- LLM processing: 3 seconds average

**Calculation**:
- **Cache misses** (80%): Limited by semaphore=5
- **LLM throughput**: ~1.67 req/s
- **Total throughput**: 1.67 / 0.8 = **~2.1 requests/second** = **~125 requests/minute**

## Summary: Expected Throughput

### Requests Per Second:

| Scenario | Cache Hit Rate | Requests/Second | Notes |
|----------|----------------|-----------------|-------|
| **Worst Case** | 0% | **0.67** | All requests hit LLM, semaphore=5 |
| **Pessimistic** | 20% | **2.1** | Low cache, semaphore limited |
| **Realistic** | 60% | **4.2** | Typical production scenario |
| **Optimistic** | 80% | **8.3** | High cache hit rate |
| **Best Case** | 100% | **50-100+** | All cached, limited by API |

### Requests Per Minute:

| Scenario | Cache Hit Rate | Requests/Minute | Notes |
|----------|----------------|-----------------|-------|
| **Worst Case** | 0% | **~40** | All requests hit LLM |
| **Pessimistic** | 20% | **~125** | Low cache |
| **Realistic** | 60% | **~250** | Typical production |
| **Optimistic** | 80% | **~500** | High cache |
| **Best Case** | 100% | **~3,000-6,000** | All cached |

## Bottleneck Analysis

### Primary Bottleneck: LLM Processing

**Current Limits**:
- **OLLAMA_NUM_PARALLEL=2**: Only 2 requests process simultaneously
- **Semaphore=5**: Only 5 requests can queue for LLM
- **LLM processing time**: ~3 seconds per request

**Impact**:
- Maximum LLM throughput: ~1.67 requests/second
- This limits overall system throughput to ~2-8 req/s (depending on cache)

### Secondary Bottlenecks:

1. **Semaphore Limit (5)**:
   - Prevents more than 5 concurrent LLM requests
   - Causes queueing and increased latency
   - **Solution**: Increase semaphore (but requires more memory)

2. **OLLAMA_NUM_PARALLEL (2)**:
   - Limits active processing to 2 requests
   - **Solution**: Increase to 4-8 (but requires more memory)

3. **Cache Hit Rate**:
   - Lower cache hit rate = more LLM requests = lower throughput
   - **Solution**: Improve caching strategy, warm cache

## Rate Limiting Impact

**Current Rate Limit**: 60 requests/minute (if enabled)

**Comparison**:
- **Worst case throughput**: ~40 req/min (all cache misses)
- **Realistic throughput**: ~250 req/min (60% cache)
- **Rate limit**: 60 req/min

**Impact**: 
- ⚠️ **Rate limit is lower than realistic throughput!**
- Rate limit will cap throughput to **60 requests/minute** = **1 request/second**
- **Recommendation**: Increase rate limit or disable for high-load scenarios

## Performance Under Different Loads

### Low Load (< 10 concurrent users):
- **Throughput**: ~4-8 requests/second
- **Response time**: ~3-6 seconds (cache misses), ~10ms (cache hits)
- **Status**: ✅ Comfortable

### Medium Load (10-50 concurrent users):
- **Throughput**: ~4-8 requests/second (limited by LLM)
- **Response time**: ~6-15 seconds (cache misses), ~50ms (cache hits)
- **Queue wait**: ~3-12 seconds
- **Status**: ⚠️ Acceptable, but queueing occurs

### High Load (50-200 concurrent users):
- **Throughput**: ~4-8 requests/second (still limited by LLM)
- **Response time**: ~15-60 seconds (cache misses), ~100ms (cache hits)
- **Queue wait**: ~12-57 seconds
- **Status**: ⚠️ Degraded performance, high latency

### Stress Load (> 200 concurrent users):
- **Throughput**: ~4-8 requests/second (hard limit)
- **Response time**: > 60 seconds
- **Queue wait**: > 57 seconds
- **Status**: ❌ Poor performance, timeouts likely

## Recommendations for Improving Throughput

### Short-term (No Infrastructure Changes):

1. **Increase Cache Hit Rate**:
   - Implement query normalization
   - Cache similar queries
   - Warm cache with common queries
   - **Expected improvement**: 2-4x throughput

2. **Optimize LLM Parameters**:
   - Reduce `max_tokens` from 300 to 200 (faster generation)
   - Reduce `num_ctx` from 1024 to 512 (if context allows)
   - **Expected improvement**: 1.2-1.5x throughput

3. **Increase Rate Limit** (if enabled):
   - From 60 to 300+ requests/minute
   - **Expected improvement**: Unlock full capacity

### Medium-term (Configuration Changes):

1. **Increase Semaphore** (requires more memory):
   - From 5 to 10-15
   - **Expected improvement**: 2-3x throughput

2. **Increase OLLAMA_NUM_PARALLEL** (requires more memory):
   - From 2 to 4
   - **Expected improvement**: 2x throughput

3. **Increase Memory** (requires infrastructure):
   - From 4GB to 8-10GB
   - **Expected improvement**: 2-4x throughput

### Long-term (Infrastructure Changes):

1. **Horizontal Scaling**:
   - Multiple Ollama instances
   - Load balancing
   - **Expected improvement**: Linear scaling

2. **GPU Acceleration**:
   - Use GPU for LLM inference
   - **Expected improvement**: 5-10x throughput

3. **Model Optimization**:
   - Use smaller/faster model
   - Use specialized inference engine
   - **Expected improvement**: 2-5x throughput

## Monitoring Recommendations

### Key Metrics to Track:

1. **Throughput**:
   - Requests per second
   - Requests per minute
   - Target: > 4 req/s (realistic scenario)

2. **Cache Hit Rate**:
   - Percentage of requests served from cache
   - Target: > 60%

3. **LLM Queue Length**:
   - Number of requests waiting for LLM
   - Target: < 3 requests

4. **Response Times**:
   - P50, P95, P99
   - Target: P95 < 10 seconds

5. **Error Rate**:
   - 500 errors, timeouts
   - Target: < 1%

## Conclusion

### Current Configuration Capacity:

**Realistic Throughput** (60% cache hit rate):
- **~4.2 requests/second**
- **~250 requests/minute**

**Best Case** (80% cache hit rate):
- **~8.3 requests/second**
- **~500 requests/minute**

**Worst Case** (0% cache hit rate):
- **~0.67 requests/second**
- **~40 requests/minute**

### Key Constraints:

1. **LLM Processing**: 2 parallel, ~3s each = ~0.67 req/s base
2. **Semaphore Limit**: 5 concurrent = ~1.67 req/s max LLM throughput
3. **Cache Hit Rate**: Determines actual throughput (2-8 req/s)
4. **Rate Limiting**: 60 req/min may cap throughput

### Next Steps:

1. **Monitor actual cache hit rate** in production
2. **Measure actual LLM processing time** (may vary)
3. **Adjust rate limiting** based on actual capacity
4. **Consider increasing memory** if higher throughput needed

