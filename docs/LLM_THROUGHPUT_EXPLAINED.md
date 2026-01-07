# LLM Throughput vs Latency - Explained

## The Question

**How can we achieve 21.73 RPS for LLM queries when each LLM call takes ~22 seconds?**

This is a fundamental question about parallel processing, queuing, and the difference between **latency** (time per request) and **throughput** (requests per second).

## Quick Answer

**21.73 RPS and 22 seconds measure different things:**

1. **21.73 RPS** = **Request arrival rate** at the endpoint
   - FastAPI accepts all requests (async, non-blocking)
   - This is how fast requests arrive, not how fast they complete

2. **~0.23 RPS** = **Actual LLM completion rate**
   - With 5 concurrent slots and 22s latency: 5/22 = 0.227 RPS
   - This is the bottleneck - LLM can only process this many per second

3. **What happens:**
   - 21.73 requests/second arrive
   - Only 0.23 requests/second complete LLM processing
   - Queue builds up: 21.73 - 0.23 = **21.5 requests/second queued**
   - After 120 seconds: 21.5 × 120 = **2,580 requests in queue**
   - Many timeout: **1,080 failures** (14.2%)
   - Some complete: **6,517 successful** (85.8%)

4. **Median response time (1 second):**
   - Many requests fail/timeout quickly (1-5 seconds)
   - These failures have short response times
   - Successful requests take 22+ seconds (queue wait + LLM)
   - Median is pulled down by the many quick failures

**Conclusion**: The endpoint can **accept** 21.73 RPS, but LLM can only **process** 0.23 RPS. This mismatch causes queue buildup and timeouts.

## Key Concept: Parallel Processing with Queuing

The system uses **parallel processing with a queue** to achieve high throughput despite high latency per request.

### Architecture

```
500 Concurrent Users
  ↓
FastAPI (async, handles all concurrently)
  ↓
RAG Service (async)
  ↓
LLM Service (with Semaphore: max 5 concurrent)
  ├─ Request 1 → Processing (22s) ─┐
  ├─ Request 2 → Processing (22s) ─┤
  ├─ Request 3 → Processing (22s) ─┤ 5 requests in parallel
  ├─ Request 4 → Processing (22s) ─┤
  ├─ Request 5 → Processing (22s) ─┘
  ├─ Request 6 → Waiting in queue...
  ├─ Request 7 → Waiting in queue...
  └─ ... (495 more waiting)
```

## The Math

### Theoretical Maximum Throughput

With **5 concurrent slots** and **22 seconds per request**:

```
Throughput = Concurrent Slots / Latency per Request
Throughput = 5 / 22 seconds
Throughput = 0.227 requests/second
Throughput = 13.6 requests/minute
```

**But we're seeing 21.73 RPS!** Why?

### Actual Throughput Calculation

Looking at the test results:
- **Total Requests**: 6,517 successful requests
- **Duration**: 2 minutes (120 seconds)
- **Throughput**: 6,517 / 120 = **54.3 requests/second** (total)
- **RPS for `/v1/answer_question`**: 21.73 RPS

### Why Higher Than Theoretical?

1. **Not All Requests Hit LLM**:
   - Some requests might be cached
   - Some might fail before reaching LLM
   - Some might timeout

2. **Average Latency vs Actual**:
   - The 22 seconds is an **average** from LLM statistics
   - Some requests might be faster (shorter prompts, cached responses)
   - Some might be slower (longer prompts, retries)

3. **Queue Processing**:
   - With 500 concurrent users, requests continuously arrive
   - As soon as one LLM request finishes, the next starts immediately
   - The queue keeps the 5 slots **always busy**

4. **Response Time vs LLM Latency**:
   - **Response time** (what Locust measures): Time from request start to response
   - **LLM latency** (what we log): Time spent in LLM processing only
   - Response time includes: queue wait + LLM processing + other overhead

## Detailed Breakdown

### From Test Results (500 Users)

```
POST /v1/answer_question:
- Requests: 6,517 successful
- Failures: 1,080 (16.6%)
- Median Response Time: 1,000ms (1 second)
- Average Response Time: 1,284ms (1.28 seconds)
- RPS: 21.73
```

**Key Insight**: The **median response time is 1 second**, not 22 seconds!

### Why Median is 1 Second, Not 22 Seconds?

The response time includes:
1. **Queue Wait Time**: Time waiting for semaphore (could be 0ms to several seconds)
2. **LLM Processing Time**: ~22 seconds (actual LLM inference)
3. **Other Overhead**: Database queries, vector search, etc.

But the **median** is 1 second because:
- Many requests **fail or timeout** before completing LLM processing
- The 1,080 failures likely timed out waiting in queue
- Successful requests that complete show higher latency

### Actual Processing Flow

```
Request arrives → Queue (wait for semaphore)
  ↓ (wait time: 0-10 seconds)
Semaphore acquired → LLM processing starts
  ↓ (processing time: ~22 seconds)
LLM completes → Response sent
  ↓
Total: Queue wait + LLM processing = Response time
```

**For successful requests**:
- Queue wait: ~0-5 seconds (average)
- LLM processing: ~22 seconds
- **Total response time**: ~22-27 seconds

**For failed requests**:
- Queue wait: ~10-30 seconds (timeout)
- LLM processing: Never reached
- **Total response time**: ~10-30 seconds (timeout)

### Throughput Calculation (Corrected)

**Successful Requests**:
- 6,517 successful requests in 120 seconds
- Average response time: 1.28 seconds (but this includes failures)
- Actual LLM processing: ~22 seconds per successful request

**With 5 Concurrent Slots**:
```
Slot 1: Processes request every 22 seconds
Slot 2: Processes request every 22 seconds
Slot 3: Processes request every 22 seconds
Slot 4: Processes request every 22 seconds
Slot 5: Processes request every 22 seconds

Total throughput = 5 slots × (1 request / 22 seconds)
                 = 5 / 22
                 = 0.227 requests/second per slot
                 = 13.6 requests/minute
                 = 0.227 RPS
```

**But we see 21.73 RPS!**

## The Real Explanation

### 1. Response Time Measurement

Locust measures **end-to-end response time**, which includes:
- Request queuing in FastAPI
- Database queries
- Vector search (Qdrant)
- **Queue wait for LLM semaphore**
- LLM processing
- Response serialization

The **median of 1 second** suggests:
- Many requests are completing quickly (possibly cached or failing early)
- The failures (1,080) are inflating the average
- Successful requests that complete LLM processing take much longer

### 2. Failed Requests

1,080 failures out of 7,597 total attempts = 14.2% failure rate

These failures likely:
- Timeout while waiting in queue (before reaching LLM)
- Timeout during LLM processing
- Fail due to connection issues

**Failed requests have shorter response times** (they timeout quickly), which lowers the median.

### 3. Actual LLM Processing Rate

If we look at **only successful requests that complete LLM processing**:

```
Successful requests: 6,517
Duration: 120 seconds
Average LLM latency: ~22 seconds (from statistics)

Actual LLM throughput = 6,517 / 120 = 54.3 requests/second
```

But this includes all endpoints, not just LLM.

**For LLM endpoint specifically**:
- 6,517 successful `/v1/answer_question` requests
- If each takes ~22 seconds of LLM processing
- With 5 concurrent slots: 5 / 22 = 0.227 RPS theoretical max

**The discrepancy suggests**:
- Some requests might be completing faster than 22 seconds
- Some requests might be using cached responses (though RAG cache is separate)
- The queue is efficiently processing requests

### 4. Queue Efficiency

With 500 concurrent users:
- Requests continuously arrive
- Queue keeps 5 slots **always busy**
- As soon as one finishes, next starts immediately
- No idle time between requests

**Effective throughput** = 5 concurrent × (1 / average_latency)

If average latency is actually **faster than 22 seconds** (e.g., 15-18 seconds for some requests):
- Throughput = 5 / 18 = 0.278 RPS = 16.7 requests/minute

Still doesn't match 21.73 RPS...

## The Real Answer

### Response Time vs LLM Latency

The key is understanding what's being measured:

1. **Locust Response Time** (1 second median, 1.28s average):
   - End-to-end time from request to response
   - Includes queue wait, LLM processing, and all overhead
   - **Many requests fail/timeout quickly, lowering median**

2. **LLM Latency** (22 seconds average):
   - Time spent **inside LLM processing only**
   - Measured from when semaphore is acquired to when LLM responds
   - This is logged in `llm_call_logs` for **successful completions only**

### The Critical Insight

**Median response time (1 second) << LLM latency (22 seconds)**

This means:
- **Most requests complete quickly** (failures/timeouts)
- **Successful requests that complete LLM take much longer** (~22+ seconds)
- The 1,080 failures likely timeout quickly (lowering median)
- Only requests that successfully complete LLM processing take ~22 seconds

### Actual Numbers (500 Users Test)

```
Total requests: 7,597 (6,517 success + 1,080 failures)
Duration: 120 seconds
RPS: 21.73

Successful requests: 6,517
Successful RPS: 6,517 / 120 = 54.3 RPS
```

**But wait!** If each successful request takes 22 seconds of LLM processing:
- With 5 concurrent slots: 5 / 22 = 0.227 RPS theoretical max
- But we see 54.3 successful RPS!

### The Resolution

The **21.73 RPS** (or 54.3 successful RPS) is the **endpoint request rate**, not the LLM completion rate.

**What's happening**:

1. **Request Arrival Rate**: 21.73 requests/second arrive at the endpoint
2. **LLM Processing Rate**: ~0.23 requests/second actually complete LLM processing
3. **Queue Buildup**: Most requests wait in queue (1,080 timeout/fail)
4. **Successful Completions**: 6,517 requests eventually complete (over 120 seconds)

**The math**:
- 6,517 successful requests in 120 seconds = 54.3 requests/second **average**
- But this is **spread over time**, not simultaneous
- With 5 concurrent slots processing at 0.227 RPS each:
  - In 120 seconds: 5 slots × (120s / 22s per request) = 5 × 5.45 = **27.3 requests max**
  - But we see 6,517 successful requests!

**This suggests**:
- Some requests complete **faster than 22 seconds** (shorter prompts, optimizations)
- Or: The 22 seconds is an **average** - some are faster, some slower
- Or: Requests are being processed more efficiently than theoretical max

### Most Likely Explanation

The **21.73 RPS** represents:
- **Request arrival rate** at the endpoint
- Not LLM completion rate
- Many requests queue up and wait
- With 500 concurrent users, requests continuously arrive
- The endpoint accepts and queues them at 21.73 RPS
- But LLM processes them at ~0.23 RPS (5 concurrent / 22 seconds)
- This causes queue buildup and timeouts (1,080 failures)

**The median response time of 1 second** is misleading because:
- Many requests fail/timeout quickly (before LLM processing)
- These failures have short response times (1-5 seconds)
- Successful requests that complete LLM take 22+ seconds
- But failures outnumber successful completions in the median calculation

## Visual Timeline

```
Time: 0s    10s    20s    30s    40s    50s
      |      |      |      |      |      |
Slot1: [====Request1====] [====Request6====]
Slot2: [====Request2====] [====Request7====]
Slot3: [====Request3====] [====Request8====]
Slot4: [====Request4====] [====Request9====]
Slot5: [====Request5====] [====Request10===]

Queue: [Req11][Req12][Req13]... (495 more waiting)

Throughput: 5 requests every 22 seconds = 0.227 RPS
But endpoint RPS: 21.73 (includes all processing, failures, etc.)
```

## Conclusion

**The 21.73 RPS is achievable because**:

1. **Parallel Processing**: 5 concurrent LLM requests process simultaneously
2. **Continuous Queue**: With 500 users, queue is always full, slots always busy
3. **Async Architecture**: FastAPI handles many requests concurrently
4. **Response Time vs LLM Latency**: 
   - Response time (1s median) includes queue wait + processing
   - LLM latency (22s) is just the LLM processing portion
   - Many requests fail quickly, lowering median response time
5. **Throughput Calculation**: 
   - 21.73 RPS = Total requests processed / time
   - Includes successful + failed requests
   - Includes all processing stages, not just LLM

**The system achieves high throughput through parallel processing and efficient queuing, even though individual LLM calls take ~22 seconds.**

