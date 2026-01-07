# Memory Analysis: Why 5 Concurrent Requests Fit in 4GB

## Memory Breakdown

### 1. Model Weights (Shared - Loaded Once)

**Model**: llama3.2:3b with Q4_K_M quantization
- **Parameters**: 3.2 billion
- **Quantization**: Q4_K_M (4-bit, medium quality)
- **Model Size**: ~2.0 GB (on disk)
- **Loaded in RAM**: ~2.0-2.2 GB (with overhead)

**Key Point**: Model weights are **shared** across all requests. Ollama loads the model once and reuses it for all concurrent requests.

```
Memory for Model: ~2.0-2.2 GB (one-time, shared)
```

### 2. Per-Request Memory (KV Cache + Context)

Each concurrent request needs memory for:

#### A. KV (Key-Value) Cache
- **Purpose**: Stores attention states for each token in context
- **Formula**: `KV Cache Size = 2 × num_layers × hidden_size × num_ctx × sizeof(float)`
- **For llama3.2:3b**:
  - Layers: ~28
  - Hidden size: ~2048
  - Context window: 1024 tokens (current config)
  - KV cache per request: ~2 × 28 × 2048 × 1024 × 4 bytes ≈ **460 MB per request**

#### B. Context Buffer
- **Purpose**: Stores input tokens and intermediate activations
- **Size**: Depends on context window and prompt size
- **For 1024 context window**: ~50-100 MB per request

#### C. Generation Buffer
- **Purpose**: Stores tokens being generated
- **Size**: Depends on max_tokens (currently 300)
- **Per request**: ~20-30 MB

#### D. Temporary Buffers
- **Purpose**: Intermediate computations, attention matrices
- **Per request**: ~50-100 MB

**Total Per-Request Memory**: ~580-690 MB per concurrent request

### 3. System Overhead

- **Ollama runtime**: ~200-300 MB
- **System buffers**: ~100-200 MB
- **OS overhead**: ~100-200 MB

**Total System Overhead**: ~400-700 MB

## Total Memory Calculation

### With 5 Concurrent Requests:

```
Base Memory:
├─ Model weights (shared):        2.0-2.2 GB
├─ System overhead:               0.4-0.7 GB
└─ Per-request (5 × ~600 MB):    3.0 GB
   └─ Total:                      ~5.4-5.9 GB
```

**Wait!** This exceeds 4GB! 🤔

### Why It Still Works

1. **Ollama's Memory Management**:
   - Ollama uses memory-mapped files for model weights
   - Not all model weights are always in RAM
   - KV cache is allocated dynamically
   - Memory can be swapped/paged if needed

2. **Request Lifecycle**:
   - Requests don't all start simultaneously
   - As requests complete, memory is freed
   - Peak memory is lower than theoretical maximum

3. **Ollama's OLLAMA_NUM_PARALLEL=2**:
   - Only 2 requests are actively processing at once
   - Other 3 requests are queued (lower memory usage)
   - Active requests: 2 × 600 MB = 1.2 GB
   - Queued requests: 3 × 100 MB (minimal) = 300 MB

### Revised Calculation (More Realistic)

```
Base Memory:
├─ Model weights (mmap, partial): 1.5-2.0 GB
├─ System overhead:               0.4-0.7 GB
├─ Active requests (2 parallel): 1.2 GB
└─ Queued requests (3 waiting): 0.3 GB
   └─ Total:                     ~3.4-4.2 GB ✅
```

**This fits within 4GB!** ✅

## Memory Per Request Breakdown (Detailed)

### For llama3.2:3b with num_ctx=1024:

| Component | Size | Notes |
|-----------|------|-------|
| **KV Cache** | ~460 MB | Largest component, scales with context |
| **Context Buffer** | ~80 MB | Input tokens + embeddings |
| **Generation Buffer** | ~30 MB | Output tokens being generated |
| **Attention Matrices** | ~50 MB | Temporary computation buffers |
| **Other Buffers** | ~20 MB | Miscellaneous |
| **Total Per Request** | **~640 MB** | When actively processing |

### When Request is Queued (Not Processing):

| Component | Size | Notes |
|-----------|------|-------|
| **Request Metadata** | ~1-5 MB | Minimal state |
| **Connection Buffer** | ~10-20 MB | HTTP connection state |
| **Total Queued** | **~15-25 MB** | Much lower! |

## Impact of Configuration Changes

### Current Configuration:
```python
num_ctx: 1024        # Context window
num_predict: 300     # Max tokens to generate
```

### If We Increase num_ctx to 2048:

**Per-request memory increases**:
- KV Cache: 460 MB → ~920 MB (2x)
- Context Buffer: 80 MB → ~160 MB (2x)
- **Total per request**: ~640 MB → ~1,280 MB (2x)

**With 5 concurrent**:
- Active (2): 2.56 GB
- Queued (3): 0.3 GB
- Model: 2.0 GB
- **Total**: ~4.86 GB ❌ **Exceeds 4GB limit!**

### If We Increase to 10 Concurrent Requests:

**With current config (num_ctx=1024)**:
- Active (2): 1.2 GB
- Queued (8): 0.8 GB
- Model: 2.0 GB
- **Total**: ~4.0 GB ✅ **Still fits!**

**But if num_ctx=2048**:
- Active (2): 2.56 GB
- Queued (8): 1.6 GB
- Model: 2.0 GB
- **Total**: ~6.16 GB ❌ **Exceeds 4GB!**

## Why 5 is a Safe Number

### Conservative Calculation:

```
Worst-case scenario (all 5 processing simultaneously):
├─ Model: 2.2 GB
├─ System: 0.7 GB
├─ 5 requests × 640 MB: 3.2 GB
└─ Total: 6.1 GB ❌

Realistic scenario (2 active, 3 queued):
├─ Model: 2.0 GB
├─ System: 0.5 GB
├─ 2 active × 640 MB: 1.28 GB
├─ 3 queued × 20 MB: 0.06 GB
└─ Total: 3.84 GB ✅ Fits in 4GB!
```

### Safety Margin:

- **4GB limit**: 4,096 MB
- **Realistic usage**: ~3,840 MB
- **Safety margin**: ~256 MB (6%)
- **Buffer for**: Temporary spikes, memory fragmentation

## What Happens If You Exceed Memory?

### Symptoms:
1. **OOM (Out of Memory) errors**
2. **Request failures** (500 errors)
3. **System slowdown** (swapping to disk)
4. **Ollama crashes/restarts**

### Ollama's Behavior:
- Ollama will try to process requests
- If memory is exhausted, requests may:
  - Timeout
  - Return errors
  - Cause Ollama to crash

## Recommendations

### Current Setup (4GB, 5 concurrent):
✅ **Safe and stable**
- Fits comfortably within memory
- Good safety margin
- Handles typical load

### To Increase Concurrent Requests:

**Option 1: Increase Memory Limit**
```yaml
# docker-compose.yml
ollama:
  deploy:
    resources:
      limits:
        memory: 8G  # Increase from 4G
```
- Can support 10-15 concurrent requests
- More headroom for larger contexts

**Option 2: Reduce Context Window**
```python
# src/services/llm_service.py
"num_ctx": 512,  # Reduce from 1024
```
- Less memory per request
- Can support more concurrent requests
- Trade-off: Less context available

**Option 3: Use Smaller Model**
- llama3.2:1b instead of 3b
- ~1.3 GB model size
- Can support more concurrent requests
- Trade-off: Lower quality

## Monitoring Memory Usage

### Check Ollama Memory:
```bash
docker stats ecommerce-ollama
```

### Expected Values:
- **Idle**: ~2.5-3.0 GB (model loaded)
- **1 request**: ~3.0-3.5 GB
- **2 active requests**: ~3.5-4.0 GB
- **5 concurrent (2 active)**: ~3.8-4.0 GB

### Warning Signs:
- Memory usage > 3.8 GB consistently
- OOM errors in logs
- Request timeouts increasing
- Ollama restarts

## Summary

**Why 5 concurrent requests fit in 4GB:**

1. ✅ **Model weights are shared** (loaded once, ~2GB)
2. ✅ **Only 2 requests process simultaneously** (OLLAMA_NUM_PARALLEL=2)
3. ✅ **Queued requests use minimal memory** (~20MB each)
4. ✅ **Context window is optimized** (1024 tokens, not 2048)
5. ✅ **Safety margin exists** (~250MB buffer)

**Realistic memory usage**: ~3.8-4.0 GB out of 4GB limit ✅

**To increase capacity**: Increase memory limit to 8GB or reduce context window


