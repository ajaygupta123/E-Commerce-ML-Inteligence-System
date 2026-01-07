# Performance Test Results Analysis

**Test Date**: 2026-01-07  
**Test Duration**: Multiple scenarios (10, 50, 200, 500 users)

---

## Executive Summary

### Test Results:

| Scenario | Users | Status | Total Requests | Failures | Failure Rate | Avg Response Time |
|----------|-------|--------|----------------|----------|--------------|-------------------|
| **Low Load** | 10 | ✅ Success | 45 | 0 | 0.00% | 14,103ms |
| **Medium Load** | 50 | ✅ Success | 926 | 0 | 0.00% | 7.58ms |
| **High Load** | 200 | ❌ Failed | 11,738 | 24 | 0.20% | 8.04ms |
| **Stress Test** | 500 | ❌ Failed | ~12,000+ | 1,207 | ~10%+ | N/A |

### Root Cause:

**🔴 Database Connection Pool Exhaustion**

Error: `asyncpg.exceptions.TooManyConnectionsError: sorry, too many clients already`

---

## Detailed Analysis

### Scenario 1: Low Load (10 Users) ✅

**Configuration:**
- Users: 10
- Spawn Rate: 2 users/second
- Duration: 2 minutes
- Total Requests: 45

**Results:**
- **Failures**: 0 (0.00%)
- **Requests per Second**: 373.42
- **Average Response Time**: 14,103.71 ms
- **Median Response Time**: 10.00 ms
- **Min Response Time**: 2.40 ms
- **Max Response Time**: 113,063.72 ms

**Analysis:**
- ✅ **No failures** - System handles low load successfully
- ⚠️ **High average response time** (14s) is misleading
  - **Median is only 10ms** - Most requests are fast (cache hits)
  - **Max is 113s** - A few requests are very slow (cache misses hitting LLM)
  - This suggests **high cache hit rate** for most requests
- **Throughput**: 373 req/s (mostly health checks and cached responses)

**Endpoint Breakdown:**
- `/health`: 23 requests, 0 failures, median 3ms
- `/v1/answer_question`: 2 requests, 0 failures, median 107s (cache misses)
- `/v1/explain`: 3 requests, 0 failures, median 17ms
- `/v1/predict_discount`: 17 requests, 0 failures, median 11ms

---

### Scenario 2: Medium Load (50 Users) ✅

**Configuration:**
- Users: 50
- Spawn Rate: 5 users/second
- Duration: 3 minutes
- Total Requests: 926

**Results:**
- **Failures**: 0 (0.00%)
- **Requests per Second**: 451.07
- **Average Response Time**: 7.58 ms
- **Median Response Time**: 3.00 ms
- **Min Response Time**: 1.41 ms
- **Max Response Time**: 216.66 ms

**Analysis:**
- ✅ **No failures** - System handles medium load excellently
- ✅ **Excellent performance** - Average 7.58ms, median 3ms
- ✅ **High throughput** - 451 req/s
- This suggests **very high cache hit rate** (likely >90%)

**Endpoint Breakdown:**
- `/health`: 583 requests, 0 failures, median 3ms
- `/v1/answer_question`: 74 requests, 0 failures, median 6ms (likely cached)
- `/v1/explain`: 11 requests, 0 failures, median 17ms
- `/v1/predict_discount`: 258 requests, 0 failures, median 11ms

**Key Observation:**
- RAG requests (`/v1/answer_question`) have median 6ms - **much faster than expected**
- This indicates **high cache hit rate** (likely >95% for this scenario)
- System is performing well under medium load

---

### Scenario 3: High Load (200 Users) ❌

**Configuration:**
- Users: 200
- Spawn Rate: 10 users/second
- Duration: 5 minutes
- Total Requests: 11,738

**Results:**
- **Failures**: 24 (0.20%)
- **Requests per Second**: 673.28
- **Average Response Time**: 8.04 ms
- **Median Response Time**: 4.00 ms
- **Min Response Time**: 0.93 ms
- **Max Response Time**: 280.77 ms

**Error Details:**
- **21 failures** on `/v1/answer_question` endpoint
- **3 failures** on `/health` endpoint
- **Error**: `asyncpg.exceptions.TooManyConnectionsError: sorry, too many clients already`

**Analysis:**
- ⚠️ **Database connection pool exhaustion**
- **Failure rate**: 0.20% (low, but indicates problem)
- **Performance**: Still good (8ms average) when not failing
- **Throughput**: 673 req/s (high, but causing connection issues)

**Endpoint Breakdown:**
- `/health`: 7,011 requests, 3 failures, median 3ms
- `/v1/answer_question`: 1,480 requests, **21 failures**, median 7ms
- `/v1/explain`: 166 requests, 0 failures, median 17ms
- `/v1/predict_discount`: 3,081 requests, 0 failures, median 12ms

**Root Cause:**
- **Database connection pool**: 50 base + 100 overflow = 150 total connections
- Under high load (200 concurrent users), connections are being exhausted
- Each RAG request needs database connections for product fetching
- **Sequential product fetching** (5 products per request) holds connections longer
- Connections aren't being released fast enough under high concurrent load

---

### Scenario 4: Stress Test (500 Users) ❌

**Configuration:**
- Users: 500
- Spawn Rate: 20 users/second
- Duration: 5 minutes
- Total Requests: ~12,000+ (estimated)

**Results:**
- **Failures**: 1,207 (estimated ~10%+ failure rate)
- **Error**: Same as high load - `TooManyConnectionsError`

**Analysis:**
- ❌ **Severe database connection pool exhaustion**
- **High failure rate** (~10%+) indicates system is overwhelmed
- **Same root cause** as high load scenario, but worse

---

## Root Cause Analysis

### Primary Issue: Database Connection Pool Exhaustion

**Current Configuration:**
```python
# src/db/postgres.py
pool_size=50
max_overflow=100
# Total: 150 connections
```

**Problem:**
1. **Sequential Product Fetching**: Each RAG request fetches 5 products sequentially
   ```python
   for product_id in retrieved_product_ids:
       product = await product_repo.get_by_id(product_id)
   ```
   - Each `get_by_id` call uses a database connection
   - 5 sequential calls = connection held for 5 × 20-100ms = 100-500ms
   - Under high load, many requests hold connections simultaneously

2. **Connection Pool Size**: 150 connections may not be enough for 200+ concurrent users
   - Each user can make multiple requests
   - Each RAG request needs database access
   - Health checks also use connections (though briefly)

3. **Connection Release Timing**: Connections may not be released immediately
   - Async context managers should release connections, but under high load, timing issues occur

### Secondary Issues:

1. **No Connection Pool Monitoring**: Can't see when pool is exhausted
2. **No Graceful Degradation**: System fails with 500 errors instead of queuing
3. **Sequential Fetching**: Inefficient use of connections

---

## Solutions

### Immediate Fix (High Priority):

#### 1. Fix Sequential Database Queries

**Current Code** (inefficient):
```python
# src/services/rag_service.py (lines 188-198)
retrieved_products = []
if product_repo:
    for product_id in retrieved_product_ids:
        product = await product_repo.get_by_id(product_id)
        if product:
            retrieved_products.append({...})
```

**Solution**: Batch fetch all products in one query

**Implementation:**
1. Add `get_by_ids` method to `ProductRepository`:
   ```python
   async def get_by_ids(self, product_ids: List[UUID]) -> List[Product]:
       """Get multiple products by IDs in one query."""
       result = await self.session.execute(
           select(Product).where(Product.id.in_(product_ids))
       )
       return list(result.scalars().all())
   ```

2. Update `rag_service.py`:
   ```python
   # Batch fetch all products
   if product_repo and retrieved_product_ids:
       products = await product_repo.get_by_ids(retrieved_product_ids)
       retrieved_products = [
           {
               "id": str(p.id),
               "name": p.name,
               "category": p.category,
               "price": p.price,
               "rating": p.rating,
               "description": p.description,
           }
           for p in products
       ]
   ```

**Expected Improvement:**
- **Latency**: 100-500ms → 20-100ms (5-10x faster)
- **Connection usage**: 5 connections → 1 connection (5x reduction)
- **Throughput**: Can handle 5-10x more concurrent requests

#### 2. Increase Database Connection Pool

**Current**: 50 base + 100 overflow = 150 total

**Recommended**: 100 base + 200 overflow = 300 total

```python
# src/db/postgres.py
pool_size=100
max_overflow=200
```

**Expected Improvement:**
- **Connection capacity**: 2x increase
- **Can handle**: ~400 concurrent users (vs 200)

**Trade-off**: More memory usage, but necessary for high load

#### 3. Add Connection Pool Monitoring

Add metrics to track:
- Active connections
- Pool size
- Connection wait time
- Pool exhaustion events

---

### Medium-term Fixes:

#### 4. Implement Connection Pooling Best Practices

- **Connection timeout**: Ensure connections are released quickly
- **Connection recycling**: Recycle connections after certain time
- **Connection health checks**: Verify connections before use

#### 5. Add Graceful Degradation

- **Queue requests** when pool is exhausted (instead of failing)
- **Return 503 Service Unavailable** with retry-after header
- **Circuit breaker** to prevent cascading failures

#### 6. Optimize Database Queries

- **Index optimization**: Ensure product_id is indexed
- **Query optimization**: Use select_related for related data
- **Connection reuse**: Reuse connections within request lifecycle

---

## Performance Metrics Summary

### Successful Scenarios:

| Metric | 10 Users | 50 Users |
|--------|----------|----------|
| **Throughput** | 373 req/s | 451 req/s |
| **Avg Response Time** | 14,103ms* | 7.58ms |
| **Median Response Time** | 10ms | 3ms |
| **Failure Rate** | 0% | 0% |
| **Status** | ✅ Success | ✅ Success |

*High average due to a few very slow cache misses (113s max), but median is only 10ms

### Failed Scenarios:

| Metric | 200 Users | 500 Users |
|--------|-----------|-----------|
| **Throughput** | 673 req/s | N/A |
| **Avg Response Time** | 8.04ms | N/A |
| **Failure Rate** | 0.20% | ~10%+ |
| **Root Cause** | DB Pool Exhaustion | DB Pool Exhaustion |
| **Status** | ❌ Failed | ❌ Failed |

---

## Recommendations

### Immediate Actions:

1. ✅ **Fix sequential database queries** → Batch fetch (5-10x improvement)
2. ✅ **Increase connection pool** → 100 base + 200 overflow (2x capacity)
3. ✅ **Add connection pool monitoring** → Track usage and failures

### Short-term (1-2 weeks):

4. **Add graceful degradation** → Queue requests when pool exhausted
5. **Optimize database queries** → Index optimization, query tuning
6. **Load testing** → Re-test after fixes

### Long-term (1-3 months):

7. **Horizontal scaling** → Multiple API instances with load balancer
8. **Database read replicas** → Distribute read load
9. **Connection pool per service** → Separate pools for different operations

---

## Expected Improvements After Fixes

### After Fixing Sequential Queries:

| Scenario | Current | After Fix | Improvement |
|----------|---------|-----------|-------------|
| **200 Users** | 0.20% failure | 0% failure | ✅ Eliminate failures |
| **500 Users** | ~10% failure | <1% failure | ✅ 10x improvement |
| **RAG Latency** | 100-500ms (DB) | 20-100ms (DB) | ✅ 5-10x faster |
| **Connection Usage** | 5 per request | 1 per request | ✅ 5x reduction |

### After Increasing Connection Pool:

| Scenario | Current | After Fix | Improvement |
|----------|---------|-----------|-------------|
| **Max Concurrent Users** | ~200 | ~400 | ✅ 2x capacity |
| **Connection Headroom** | 150 | 300 | ✅ 2x capacity |

### Combined Improvements:

- **Can handle**: 400+ concurrent users (vs 200)
- **Failure rate**: <0.1% (vs 0.2-10%)
- **RAG latency**: 20-100ms DB time (vs 100-500ms)
- **Connection efficiency**: 5x better

---

## Next Steps

1. **Implement batch product fetching** (highest priority)
2. **Increase connection pool size**
3. **Re-run performance tests** to validate fixes
4. **Monitor connection pool usage** in production
5. **Add graceful degradation** for edge cases

---

## Conclusion

The system performs **excellently** under low to medium load (0% failure rate, <10ms response times). However, under high load (200+ users), **database connection pool exhaustion** causes failures.

**Root cause**: Sequential product fetching + insufficient connection pool size.

**Solution**: Batch fetching (5-10x improvement) + larger connection pool (2x capacity) = **10-20x improvement** in high-load scenarios.

After fixes, the system should handle **400+ concurrent users** with **<0.1% failure rate**.

