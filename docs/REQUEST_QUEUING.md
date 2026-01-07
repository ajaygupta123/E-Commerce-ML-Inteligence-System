# Request Queuing Implementation

## Overview

The request queuing system prevents overwhelming Ollama LLM service under high concurrent load by limiting the number of simultaneous requests using Python's `asyncio.Semaphore`.

## How It Works

### 1. Semaphore Initialization

```python
# In LLMService.__init__()
self.semaphore = asyncio.Semaphore(max_concurrent_requests)
```

- **Default**: 5 concurrent requests maximum
- **Purpose**: Acts as a "ticket system" - only 5 requests can proceed at once
- **Type**: `asyncio.Semaphore` - a concurrency control primitive

### 2. Request Flow

When a request comes in:

```python
async def generate(self, prompt: str, ...):
    # This line is the key - it acquires a "ticket"
    async with self.semaphore:
        # Only 5 requests can be here at the same time
        # All others wait in the queue
        response = await self.client.post(...)
        return content
```

### 3. How Semaphore Works

**Semaphore Behavior:**
- **Available slots**: 5 (default)
- **When a request arrives**:
  1. If slot available → Request proceeds immediately
  2. If all slots taken → Request **waits** (queued automatically by asyncio)
  3. When a request completes → Releases slot → Next queued request proceeds

**Example Scenario (5 concurrent limit):**

```
Time  | Request | Status
------|---------|--------
T0    | Req 1   | ✅ Processing (Slot 1/5)
T0    | Req 2   | ✅ Processing (Slot 2/5)
T0    | Req 3   | ✅ Processing (Slot 3/5)
T0    | Req 4   | ✅ Processing (Slot 4/5)
T0    | Req 5   | ✅ Processing (Slot 5/5)
T0    | Req 6   | ⏳ Waiting in queue...
T0    | Req 7   | ⏳ Waiting in queue...
T0    | Req 8   | ⏳ Waiting in queue...
...
T10   | Req 1   | ✅ Complete → Releases slot
T10   | Req 6   | ✅ Now processing (Slot 1/5)
```

### 4. Async Context Manager

The `async with self.semaphore:` pattern:

1. **Enters**: Acquires semaphore (gets a "ticket")
   - If available: proceeds immediately
   - If not: waits until a slot is free

2. **Executes**: Makes the HTTP request to Ollama

3. **Exits**: Releases semaphore (returns "ticket")
   - Next waiting request can now proceed

### 5. Why This Works

**Without Semaphore (Before):**
```
500 concurrent requests → All hit Ollama simultaneously
→ Ollama overwhelmed → Timeouts → 500 errors
```

**With Semaphore (After):**
```
500 concurrent requests → Only 5 hit Ollama at once
→ Remaining 495 wait in queue
→ Processed in batches of 5
→ No overwhelming → Fewer errors
```

## Implementation Details

### Singleton Pattern

The `LLMService` is created once as a singleton:

```python
# In src/api/dependencies.py
def get_rag_service() -> RAGService:
    if not hasattr(get_rag_service, '_instance'):
        get_rag_service._instance = RAGService()  # Creates LLMService() here
    return get_rag_service._instance
```

This ensures:
- **One semaphore** shared across all requests
- **Consistent queuing** across the entire application
- **Memory efficient** - no duplicate services

### Retry Logic Integration

The retry logic works **inside** the semaphore:

```python
async with self.semaphore:  # Acquire slot
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = await self.client.post(...)
            return content
        except Exception:
            # Retry without releasing semaphore
            # (still holds the slot during retries)
            await asyncio.sleep(wait_time)
```

**Important**: The semaphore slot is held during retries, preventing other requests from proceeding until the current request succeeds or exhausts retries.

## Configuration

### Adjusting Concurrency Limit

To change the maximum concurrent requests:

```python
# Option 1: Modify default in LLMService
def __init__(self, max_concurrent_requests: int = 10):  # Changed from 5 to 10
    self.semaphore = asyncio.Semaphore(max_concurrent_requests)

# Option 2: Pass when creating (requires code change)
llm_service = LLMService(max_concurrent_requests=10)
```

### Trade-offs

**Lower limit (e.g., 3):**
- ✅ More stable under load
- ✅ Less resource usage
- ❌ Slower overall throughput
- ❌ Longer wait times for queued requests

**Higher limit (e.g., 10):**
- ✅ Faster overall throughput
- ✅ Shorter wait times
- ❌ May still overwhelm Ollama
- ❌ More resource usage

**Current (5):**
- ✅ Balanced for most scenarios
- ✅ Prevents overwhelming Ollama
- ✅ Reasonable throughput

## Monitoring

To monitor queue behavior, you can add logging:

```python
async with self.semaphore:
    logger.info(f"Acquired semaphore slot. Available: {self.semaphore._value}")
    # ... make request ...
    logger.info(f"Releasing semaphore slot. Available: {self.semaphore._value}")
```

## Comparison with Other Approaches

### 1. Thread Pool Executor
```python
# Alternative approach (not used)
executor = ThreadPoolExecutor(max_workers=5)
```
- ❌ More complex
- ❌ Thread overhead
- ✅ Better for CPU-bound tasks

### 2. Rate Limiting
```python
# Alternative approach (not used)
rate_limiter = RateLimiter(calls=5, period=1)
```
- ❌ Time-based, not concurrency-based
- ❌ Doesn't prevent simultaneous requests
- ✅ Good for API rate limits

### 3. Semaphore (Current)
```python
semaphore = asyncio.Semaphore(5)
```
- ✅ Simple and efficient
- ✅ Native async support
- ✅ Automatic queuing
- ✅ Perfect for limiting concurrent I/O operations

## Summary

The queuing system uses **`asyncio.Semaphore`** to:
1. Limit concurrent Ollama requests to 5 (configurable)
2. Automatically queue excess requests
3. Process requests in order as slots become available
4. Prevent overwhelming Ollama under high load
5. Reduce 500 errors significantly

The implementation is **non-blocking** - waiting requests don't block the event loop, they just wait for their turn to proceed.


