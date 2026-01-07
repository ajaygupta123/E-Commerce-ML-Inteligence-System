# Throughput vs Latency: Why 2-5s Latency = 0.67-1.67 req/s

## The Key Concept: Parallel Processing

The relationship between latency and throughput depends on **how many requests can be processed simultaneously**.

---

## Simple Example (No Parallelism)

If you can only process **1 request at a time**:

- **Latency**: 3 seconds per request
- **Throughput**: 1 request ÷ 3 seconds = **0.33 requests/second**

**Formula**: `Throughput = 1 / Latency` (when processing sequentially)

---

## Our System: Parallel Processing

### Configuration:

- **OLLAMA_NUM_PARALLEL = 2**: 2 requests process **simultaneously**
- **Semaphore = 5**: Maximum 5 requests can be **concurrent** (2 active + 3 queued)
- **Average Latency**: 3 seconds per request

### Scenario 1: Only Active Processing (2 parallel)

```
Time 0s:  Request 1, 2 arrive → Start processing (2 active)
Time 3s:  Request 1, 2 complete → 2 requests done in 3 seconds
```

**Calculation**:
- **Latency per request**: 3 seconds
- **Parallel requests**: 2
- **Throughput**: 2 requests ÷ 3 seconds = **0.67 requests/second**

**Formula**: `Throughput = Parallel_Requests / Latency`

---

### Scenario 2: With Queue (5 concurrent)

```
Time 0s:  Request 1, 2 arrive → Start processing (2 active)
          Request 3, 4, 5 arrive → Queue (3 queued)
Time 3s:  Request 1, 2 complete → Request 3, 4 start (from queue)
Time 6s:  Request 3, 4 complete → Request 5 starts
Time 9s:  Request 5 completes
```

**Calculation**:
- **Latency per request**: 3 seconds (for active processing)
- **Total concurrent**: 5 requests (2 active + 3 queued)
- **Throughput**: 5 requests ÷ 3 seconds = **1.67 requests/second**

**But wait!** This assumes all 5 requests complete in 3 seconds, which isn't accurate.

**More Accurate Calculation**:
- **2 requests** process simultaneously
- **Every 3 seconds**, 2 requests complete
- **Throughput**: 2 requests ÷ 3 seconds = **0.67 requests/second**

**However**, with the semaphore allowing 5 concurrent:
- Requests can queue up to 5
- The system can handle 5 requests "in flight" at once
- But only 2 process simultaneously
- So throughput is still limited by the 2 parallel processing

---

## Why the Range: 0.67 to 1.67 req/s?

### Minimum Throughput (0.67 req/s):

**When**: Only 2 requests are active (no queue, or queue is empty)

```
Active Processing: 2 requests
Latency: 3 seconds
Throughput = 2 / 3 = 0.67 req/s
```

### Maximum Throughput (1.67 req/s):

**When**: Semaphore allows 5 concurrent requests, and we consider the "effective" throughput

**Calculation Method 1** (Semaphore-based):
```
Max Concurrent: 5 requests
Average Latency: 3 seconds
Throughput = 5 / 3 = 1.67 req/s
```

**But this is theoretical!** In practice, only 2 process at once.

**Calculation Method 2** (More Realistic):
```
Active Processing: 2 requests simultaneously
Queue Capacity: 3 requests
Total "in-flight": 5 requests

But throughput is still: 2 / 3 = 0.67 req/s
```

**So why 1.67 req/s?**

The 1.67 req/s comes from considering the **semaphore limit** as if it were parallel processing capacity, but this is misleading. The actual throughput is limited by **OLLAMA_NUM_PARALLEL=2**, not the semaphore.

---

## Corrected Understanding

### Actual Throughput:

**Base Throughput** (limited by OLLAMA_NUM_PARALLEL=2):
- **2 requests** process simultaneously
- **3 seconds** per request
- **Throughput**: 2 ÷ 3 = **0.67 requests/second**

**With Queue** (semaphore allows 5 concurrent):
- Still only **2 requests** process simultaneously
- **Throughput**: Still **0.67 requests/second**
- **Queue wait time**: Additional 3-6 seconds for queued requests

### Why the Confusion?

The **semaphore limit of 5** doesn't increase throughput—it just allows more requests to queue. The actual processing is still limited to 2 parallel requests.

**Think of it like this**:
- **OLLAMA_NUM_PARALLEL=2**: 2 workers processing requests
- **Semaphore=5**: 5 requests can wait in line
- **Throughput**: Still limited by the 2 workers = 0.67 req/s

---

## Visual Timeline

### With 2 Parallel Processing:

```
Time    Active Requests    Completed    Throughput
─────────────────────────────────────────────────────
0s      [Req1, Req2]       0            -
3s      [Req3, Req4]       2            2/3 = 0.67 req/s
6s      [Req5, Req6]       4            4/6 = 0.67 req/s
9s      [Req7, Req8]       6            6/9 = 0.67 req/s
```

**Steady-state throughput**: **0.67 requests/second**

### With Queue (5 Concurrent):

```
Time    Active    Queue        Completed    Throughput
─────────────────────────────────────────────────────
0s      [1,2]     [3,4,5]      0            -
3s      [3,4]     [5]           2            2/3 = 0.67 req/s
6s      [5]       []            4            4/6 = 0.67 req/s
9s      []        []            5            5/9 = 0.56 req/s (temporary)
```

**Steady-state throughput**: Still **0.67 requests/second**

The queue doesn't increase throughput—it just allows requests to wait.

---

## Corrected Throughput Calculation

### For Our System:

**Configuration**:
- **OLLAMA_NUM_PARALLEL**: 2 (active processing)
- **Semaphore**: 5 (max concurrent)
- **Average Latency**: 3 seconds

**Actual Throughput**:
```
Throughput = OLLAMA_NUM_PARALLEL / Average_Latency
           = 2 / 3
           = 0.67 requests/second
```

**Range** (if latency varies):
- **Best case** (2s latency): 2 / 2 = **1.0 req/s**
- **Average** (3s latency): 2 / 3 = **0.67 req/s**
- **Worst case** (5s latency): 2 / 5 = **0.4 req/s**

**So the correct range is**: **0.4 to 1.0 requests/second** (not 0.67 to 1.67)

---

## Why I Said 0.67-1.67 req/s

I made an error in the previous analysis. I calculated:

1. **Minimum**: 2 parallel / 3s = 0.67 req/s ✅ Correct
2. **Maximum**: 5 concurrent / 3s = 1.67 req/s ❌ **Incorrect**

The **semaphore limit of 5** doesn't increase throughput—it only allows more requests to queue. The actual throughput is always limited by **OLLAMA_NUM_PARALLEL=2**.

---

## Corrected Summary

### Actual Throughput:

**Base Throughput** (OLLAMA_NUM_PARALLEL=2):
- **Latency**: 2-5 seconds (average 3s)
- **Throughput**: 2 / 3 = **0.67 requests/second** (average)
- **Range**: 0.4 to 1.0 req/s (depending on latency)

**With Cache** (60% cache hit rate):
- **Cache hits** (60%): Very fast (~5ms), unlimited throughput
- **Cache misses** (40%): Limited by LLM = 0.67 req/s
- **Combined**: 0.67 / 0.4 = **~1.7 req/s** (if cache hits are instant)

**But wait!** This calculation assumes cache hits are instant and unlimited, which isn't realistic. The actual combined throughput depends on the ratio and processing times.

---

## The Real Formula

### For Parallel Processing:

```
Throughput = (Number_of_Parallel_Workers × Requests_per_Batch) / Average_Latency
```

**Our System**:
- **Parallel Workers**: 2 (OLLAMA_NUM_PARALLEL)
- **Requests per Batch**: 2 (process 2 at once)
- **Average Latency**: 3 seconds
- **Throughput**: (2 × 1) / 3 = **0.67 req/s**

### If We Increase Parallelism:

**If OLLAMA_NUM_PARALLEL=4**:
- **Throughput**: 4 / 3 = **1.33 req/s**

**If OLLAMA_NUM_PARALLEL=8**:
- **Throughput**: 8 / 3 = **2.67 req/s**

---

## Key Takeaway

**Latency** = Time to process ONE request (2-5 seconds)

**Throughput** = How many requests can be processed per second

**With Parallel Processing**:
- Throughput = (Parallel_Workers) / Average_Latency
- **Not** = 1 / Latency (that's for sequential processing)

**Our System**:
- **2 parallel workers** processing requests
- **3 second average latency**
- **Throughput**: 2 / 3 = **0.67 requests/second**

The **semaphore limit of 5** allows queuing but doesn't increase throughput—it just allows more requests to wait in line.

---

## Corrected Analysis

### Actual Throughput (LLM-bound):

**Base**: **0.67 requests/second** (2 parallel / 3s latency)

**Range** (if latency varies 2-5s):
- **Best**: 2 / 2 = **1.0 req/s**
- **Average**: 2 / 3 = **0.67 req/s**
- **Worst**: 2 / 5 = **0.4 req/s**

**With 60% Cache Hit Rate**:
- **Cache misses** (40%): 0.67 req/s
- **Total throughput**: 0.67 / 0.4 = **~1.7 req/s** (if cache hits are instant)

**With 80% Cache Hit Rate**:
- **Cache misses** (20%): 0.67 req/s
- **Total throughput**: 0.67 / 0.2 = **~3.3 req/s** (if cache hits are instant)

---

## Conclusion

**I apologize for the confusion in the previous analysis.**

**Corrected Understanding**:
- **Latency**: 2-5 seconds per request
- **Parallel Processing**: 2 requests simultaneously
- **Actual Throughput**: **0.4 to 1.0 requests/second** (depending on latency)
- **Average Throughput**: **0.67 requests/second**

The **semaphore limit of 5** doesn't increase throughput—it only allows more requests to queue. The actual throughput is always limited by **OLLAMA_NUM_PARALLEL=2**.

