# Memory Scaling Analysis: 4GB → 10GB

## Current Configuration (4GB)

### Memory Breakdown:
```
Model weights:        2.0 GB (shared)
System overhead:      0.5 GB
2 active requests:    1.28 GB (2 × 640 MB)
3 queued requests:    0.06 GB (3 × 20 MB)
─────────────────────────────────────
Total:               ~3.84 GB
Available:           ~0.16 GB (safety margin)
```

### Current Limits:
- **Concurrent requests (semaphore)**: 5
- **Active processing (OLLAMA_NUM_PARALLEL)**: 2
- **Memory headroom**: ~250 MB

## With 10GB Memory Limit

### Available Memory:
- **Total**: 10,240 MB
- **Model + System**: ~2,500 MB (fixed)
- **Available for requests**: ~7,740 MB

### Capacity Calculations

#### Scenario 1: Keep Current Config (num_ctx=1024)

**Per active request**: ~640 MB
**Per queued request**: ~20 MB

**Maximum concurrent requests**:
- Active requests: 7,740 MB ÷ 640 MB = **~12 active requests**
- But limited by `OLLAMA_NUM_PARALLEL=2` → Only 2 active at once
- Queued requests: (7,740 - 1,280) ÷ 20 MB = **~323 queued requests**

**Practical limit with OLLAMA_NUM_PARALLEL=2**:
- 2 active × 640 MB = 1,280 MB
- Remaining: 7,740 - 1,280 = 6,460 MB
- Queued capacity: 6,460 ÷ 20 MB = **~323 queued requests**
- **Total concurrent**: ~325 requests (2 active + 323 queued)

**But semaphore limits to 5!** So actual capacity is still 5 concurrent.

#### Scenario 2: Increase Semaphore to Match Capacity

**Recommended semaphore**: 15-20 concurrent requests

**Memory usage**:
- 2 active × 640 MB = 1,280 MB
- 13-18 queued × 20 MB = 260-360 MB
- Model + System = 2,500 MB
- **Total**: ~4,040-4,140 MB ✅ **Fits comfortably in 10GB**

#### Scenario 3: Increase OLLAMA_NUM_PARALLEL

**If we increase to OLLAMA_NUM_PARALLEL=4**:

**Memory usage**:
- 4 active × 640 MB = 2,560 MB
- Queued: (7,740 - 2,560) ÷ 20 MB = **~259 queued requests**
- Model + System = 2,500 MB
- **Total**: ~5,060 MB ✅ **Fits in 10GB**

**Recommended semaphore**: 20-30 concurrent requests

#### Scenario 4: Increase Context Window (num_ctx=2048)

**Per active request**: ~1,280 MB (2x increase)

**With OLLAMA_NUM_PARALLEL=2**:
- 2 active × 1,280 MB = 2,560 MB
- Remaining: 7,740 - 2,560 = 5,180 MB
- Queued capacity: 5,180 ÷ 20 MB = **~259 queued requests**
- **Total**: ~261 concurrent requests

**With OLLAMA_NUM_PARALLEL=4**:
- 4 active × 1,280 MB = 5,120 MB
- Remaining: 7,740 - 5,120 = 2,620 MB
- Queued capacity: 2,620 ÷ 20 MB = **~131 queued requests**
- **Total**: ~135 concurrent requests

## Performance Impact Analysis

### Throughput Improvements

#### Current (4GB, 5 concurrent, 2 parallel):
- **Active processing**: 2 requests simultaneously
- **Queue capacity**: 3 requests
- **Throughput**: ~3-5 requests/second
- **Bottleneck**: Memory (limited to 5 concurrent)

#### With 10GB, 20 concurrent, 2 parallel:
- **Active processing**: 2 requests simultaneously (unchanged)
- **Queue capacity**: 18 requests
- **Throughput**: ~3-5 requests/second (unchanged - limited by processing, not memory)
- **Bottleneck**: Processing speed (OLLAMA_NUM_PARALLEL=2)

#### With 10GB, 20 concurrent, 4 parallel:
- **Active processing**: 4 requests simultaneously (2x improvement)
- **Queue capacity**: 16 requests
- **Throughput**: ~6-10 requests/second (2x improvement)
- **Bottleneck**: CPU/GPU processing power

### Latency Impact

**Current (5 concurrent)**:
- Average wait time in queue: ~10-20 seconds
- P95 wait time: ~30-40 seconds

**With 20 concurrent**:
- Average wait time in queue: ~20-40 seconds (longer queue)
- P95 wait time: ~60-80 seconds (longer queue)

**Trade-off**: More concurrent requests = longer queue wait times

## Recommended Configuration for 10GB

### Option A: Balanced (Recommended)

```yaml
# docker-compose.yml
ollama:
  environment:
    - OLLAMA_NUM_PARALLEL=4  # Increase from 2
  deploy:
    resources:
      limits:
        memory: 10G  # Increase from 4G
```

```python
# src/services/llm_service.py
def __init__(self, max_concurrent_requests: int = 20):  # Increase from 5
```

**Results**:
- ✅ 4 requests process simultaneously (2x improvement)
- ✅ 20 concurrent requests supported
- ✅ Memory usage: ~5.0-5.5 GB (comfortable margin)
- ✅ Throughput: ~6-10 requests/second (2x improvement)
- ✅ Queue wait time: ~20-30 seconds (acceptable)

### Option B: Maximum Throughput

```yaml
# docker-compose.yml
ollama:
  environment:
    - OLLAMA_NUM_PARALLEL=8  # Maximum parallel processing
  deploy:
    resources:
      limits:
        memory: 10G
```

```python
# src/services/llm_service.py
def __init__(self, max_concurrent_requests: int = 30):  # Higher limit
```

**Results**:
- ✅ 8 requests process simultaneously (4x improvement)
- ✅ 30 concurrent requests supported
- ✅ Memory usage: ~7.5-8.0 GB (still safe)
- ✅ Throughput: ~12-20 requests/second (4x improvement)
- ⚠️ Queue wait time: ~30-50 seconds (longer)
- ⚠️ Requires powerful CPU/GPU

### Option C: Larger Context Window

```python
# src/services/llm_service.py
"num_ctx": 2048,  # Increase from 1024
```

**With OLLAMA_NUM_PARALLEL=4, 20 concurrent**:
- ✅ Better context understanding
- ✅ Memory usage: ~6.0-6.5 GB
- ⚠️ Slower processing (larger context)
- ⚠️ Throughput: ~4-6 requests/second (slightly slower)

## Bottleneck Analysis with 10GB

### Current Bottlenecks (4GB):
1. **Memory** ⚠️ Primary
2. **Processing speed** (OLLAMA_NUM_PARALLEL=2)
3. **Semaphore limit** (5 concurrent)

### With 10GB:
1. **Processing speed** ⚠️ **New Primary Bottleneck**
   - Limited by CPU/GPU power
   - OLLAMA_NUM_PARALLEL becomes the constraint
2. **Semaphore limit** (if not increased)
3. **Memory** ✅ **No longer a bottleneck**

## Cost/Benefit Analysis

### Benefits of 10GB:

1. **2-4x Throughput** (if OLLAMA_NUM_PARALLEL increased)
   - More requests processed per second
   - Better resource utilization

2. **Higher Concurrency**
   - Support 20-30 concurrent requests
   - Better handling of traffic spikes

3. **Larger Context Windows**
   - Can use 2048+ token contexts
   - Better quality responses

4. **More Safety Margin**
   - Less risk of OOM errors
   - More stable under load

### Costs:

1. **Higher Memory Usage**
   - 10GB vs 4GB (2.5x increase)
   - May require more expensive infrastructure

2. **Longer Queue Times**
   - More concurrent requests = longer waits
   - Need to balance throughput vs latency

3. **CPU/GPU Requirements**
   - Higher parallel processing needs more compute
   - May need to upgrade hardware

4. **Diminishing Returns**
   - Beyond certain point, other bottlenecks emerge
   - CPU/GPU becomes limiting factor

## Practical Recommendations

### If You Have 10GB Available:

**Step 1: Increase Memory Limit**
```yaml
# docker-compose.yml
ollama:
  deploy:
    resources:
      limits:
        memory: 10G
```

**Step 2: Increase OLLAMA_NUM_PARALLEL**
```yaml
ollama:
  environment:
    - OLLAMA_NUM_PARALLEL=4  # Start with 4, test, then increase if needed
```

**Step 3: Increase Semaphore**
```python
# src/services/llm_service.py
def __init__(self, max_concurrent_requests: int = 20):  # Increase from 5
```

**Step 4: Monitor and Tune**
- Monitor memory usage: `docker stats ecommerce-ollama`
- Monitor throughput and latency
- Adjust based on actual performance

### Expected Improvements:

| Metric | 4GB (Current) | 10GB (Optimized) | Improvement |
|--------|---------------|------------------|-------------|
| **Concurrent Requests** | 5 | 20 | 4x |
| **Active Processing** | 2 | 4 | 2x |
| **Throughput** | 3-5 req/s | 6-10 req/s | 2x |
| **Memory Usage** | ~3.8 GB | ~5.5 GB | More headroom |
| **Queue Capacity** | 3 | 16 | 5.3x |
| **OOM Risk** | Low | Very Low | ✅ |

## Monitoring After Upgrade

### Key Metrics to Track:

1. **Memory Usage**
   ```bash
   docker stats ecommerce-ollama
   ```
   - Target: < 8GB (80% of 10GB)
   - Alert if: > 9GB consistently

2. **Throughput**
   - Requests per second
   - Target: 6-10 req/s (with OLLAMA_NUM_PARALLEL=4)

3. **Queue Length**
   - Average requests waiting
   - Target: < 10 requests
   - Alert if: > 20 requests consistently

4. **Latency**
   - P50, P95, P99 response times
   - Target: P95 < 60 seconds

5. **Error Rate**
   - 500 errors
   - Target: < 1%
   - Alert if: > 5%

## Summary

### Impact of 10GB Memory:

**Capacity**:
- ✅ Support 20-30 concurrent requests (vs 5)
- ✅ 4-8 active processing (vs 2)
- ✅ 2-4x throughput improvement

**Performance**:
- ✅ Better handling of traffic spikes
- ✅ More stable under load
- ⚠️ Longer queue wait times (trade-off)

**Requirements**:
- ✅ Need to increase OLLAMA_NUM_PARALLEL (to 4-8)
- ✅ Need to increase semaphore (to 20-30)
- ✅ May need more CPU/GPU power

**Bottom Line**:
- **10GB enables 2-4x throughput improvement**
- **But requires increasing OLLAMA_NUM_PARALLEL and semaphore**
- **CPU/GPU becomes the new bottleneck**
- **Good investment if you need higher throughput**


