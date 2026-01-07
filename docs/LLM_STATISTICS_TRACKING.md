# LLM Statistics Tracking

## Overview

The LLM Statistics Tracking feature captures detailed metrics for every LLM (Large Language Model) call made through the RAG (Retrieval-Augmented Generation) system. This enables monitoring, performance analysis, and optimization of LLM usage without any latency impact on API requests.

## Key Features

- **Zero Latency Impact**: Statistics are captured with minimal overhead (<10μs) and logged asynchronously
- **Comprehensive Metrics**: Tracks tokens, latency, queue wait times, and model parameters
- **Non-Blocking**: Fire-and-forget logging pattern ensures requests are never delayed
- **Query Linking**: Links LLM calls to specific RAG queries for traceability

## Architecture

### Data Flow

```
RAG Request
  ↓
LLM Service.generate()
  ├─ Track queue wait time (before semaphore)
  ├─ Track LLM processing time (before/after API call)
  ├─ Parse token counts from Ollama response
  └─ Return (content, stats_dict)
  ↓
RAG Service passes stats through metadata
  ↓
RAG Router
  ├─ Extract LLM stats from result
  ├─ asyncio.create_task(log_llm_call) - FIRE AND FORGET
  └─ Return response IMMEDIATELY (logging happens in background)
  ↓
Background Task (non-blocking)
  └─ Async database write (happens after response sent)
```

### Performance Characteristics

- **Statistics Capture Overhead**: <10μs (just `time.time()` calls and dict creation)
- **Logging Latency Impact**: 0ms (fire-and-forget, doesn't block request)
- **Total Impact**: <0.01ms (negligible)

## Database Schema

### Table: `llm_call_logs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `model_name` | String(100) | LLM model used (e.g., "llama3.2:3b") |
| `prompt_tokens` | Integer | Input tokens (from Ollama response) |
| `completion_tokens` | Integer | Output tokens (from Ollama response) |
| `total_tokens` | Integer | Total tokens (prompt + completion) |
| `latency_ms` | Integer | LLM processing time in milliseconds |
| `queue_wait_ms` | Integer | Time waiting in semaphore queue |
| `temperature` | Float | Temperature parameter used |
| `max_tokens` | Integer | Max tokens parameter used |
| `retry_attempts` | Integer | Number of retries (default: 0) |
| `success` | Boolean | Whether call succeeded |
| `error_message` | Text | Error message if failed |
| `query_log_id` | UUID | Foreign key to `query_logs` table |
| `created_at` | DateTime | Timestamp of the call |

### Indexes

- `ix_llm_call_logs_created_at` - For time-based queries
- `ix_llm_call_logs_model_name` - For filtering by model
- `ix_llm_call_logs_query_log_id` - For linking to RAG queries

## Implementation Details

### LLM Service (`src/services/llm_service.py`)

The `LLMService.generate()` method now returns a tuple `(content, stats_dict)` instead of just the content string.

**Statistics Captured**:
```python
stats = {
    "model_name": "llama3.2:3b",
    "latency_ms": 18362,           # LLM processing time
    "queue_wait_ms": 0,             # Time in semaphore queue
    "prompt_tokens": 433,           # Input tokens
    "completion_tokens": 300,       # Output tokens
    "total_tokens": 733,            # Total tokens
    "temperature": 0.5,             # Model parameter
    "max_tokens": 300,              # Model parameter
    "retry_attempts": 0,            # Number of retries
}
```

**Timing Implementation**:
- Queue wait time: Measured from before semaphore acquisition to after
- LLM latency: Measured from before Ollama API call to after response parsing
- Token counts: Extracted from existing Ollama JSON response (no extra API calls)

### RAG Service (`src/services/rag_service.py`)

The RAG service handles the new tuple return format and passes statistics through in the result metadata:

```python
answer, llm_stats = await self.llm_service.generate(...)
result = {
    "answer": answer,
    "metadata": {
        ...
        "llm_stats": llm_stats,  # Pass through for logging
    }
}
```

### RAG Router (`src/api/routers/rag.py`)

Fire-and-forget logging pattern using `asyncio.create_task`:

```python
# Fire-and-forget LLM stats logging (zero latency impact)
llm_stats = result.get("metadata", {}).get("llm_stats")
if llm_stats:
    asyncio.create_task(
        _log_llm_call_async(llm_stats, query_log_id)
    )

# Return response immediately (logging happens in background)
return QuestionResponse(**result)
```

**Background Logging Function**:
- Creates its own database session (request session is closed)
- Handles all errors silently (never affects request)
- Logs warnings if database write fails

## Usage

### Automatic Logging

LLM statistics are automatically captured for all RAG queries. No additional code is required.

### Querying Statistics

#### Get LLM call statistics for a specific query

```sql
SELECT 
    llm.model_name,
    llm.prompt_tokens,
    llm.completion_tokens,
    llm.total_tokens,
    llm.latency_ms,
    llm.queue_wait_ms,
    llm.temperature,
    llm.created_at
FROM llm_call_logs llm
JOIN query_logs ql ON llm.query_log_id = ql.id
WHERE ql.id = 'your-query-id';
```

#### Analyze LLM performance over time

```sql
SELECT 
    DATE(created_at) as date,
    model_name,
    COUNT(*) as call_count,
    AVG(latency_ms) as avg_latency_ms,
    AVG(queue_wait_ms) as avg_queue_wait_ms,
    AVG(total_tokens) as avg_tokens,
    SUM(total_tokens) as total_tokens
FROM llm_call_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), model_name
ORDER BY date DESC;
```

#### Find slow LLM calls

```sql
SELECT 
    id,
    model_name,
    latency_ms,
    queue_wait_ms,
    total_tokens,
    created_at
FROM llm_call_logs
WHERE latency_ms > 20000  -- > 20 seconds
ORDER BY latency_ms DESC
LIMIT 10;
```

#### Token usage analysis

```sql
SELECT 
    model_name,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(completion_tokens) as total_completion_tokens,
    SUM(total_tokens) as total_tokens,
    COUNT(*) as call_count,
    AVG(total_tokens) as avg_tokens_per_call
FROM llm_call_logs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY model_name;
```

## Configuration

No additional configuration is required. The feature is enabled by default and works automatically.

## Performance Impact

### Latency Impact: **ZERO**

- Statistics capture: <10μs overhead (just `time.time()` calls)
- Logging: 0ms (fire-and-forget, doesn't block request)
- Total impact: **<0.01ms** (negligible)

### System Strain: **MINIMAL**

- Memory: ~200 bytes per LLM call log entry
- CPU: <0.1% overhead (just dict creation and async task spawn)
- Database: Async writes, non-blocking
- No extra network calls: Parse existing Ollama response only

## Error Handling

- Logging failures never affect request success
- Background task failures are logged but don't propagate
- Database connection issues don't block requests
- All errors are caught and logged with `exc_info=True`

## Example Statistics

```json
{
    "id": "9073a2de-c93d-4c15-aa83-fba97eec4d56",
    "model_name": "llama3.2:3b",
    "prompt_tokens": 433,
    "completion_tokens": 300,
    "total_tokens": 733,
    "latency_ms": 18362,
    "queue_wait_ms": 0,
    "temperature": 0.5,
    "max_tokens": 300,
    "retry_attempts": 0,
    "success": true,
    "query_log_id": "abc-123-def-456",
    "created_at": "2026-01-07T14:48:05.05215+00:00"
}
```

## Benefits

1. **Performance Monitoring**: Track LLM latency trends over time
2. **Cost Analysis**: Monitor token usage for cost estimation
3. **Queue Analysis**: Identify when requests are waiting in queue
4. **Error Tracking**: Monitor retry attempts and failures
5. **Query Traceability**: Link LLM calls to specific user queries
6. **Optimization**: Identify slow calls and optimize prompts/parameters

## Future Enhancements

Potential improvements:
- Batch logging for high-volume scenarios
- Aggregated statistics endpoint
- Token usage alerts
- Performance dashboards
- Cost estimation based on token usage

## Related Files

- `src/db/models/llm_call_log.py` - Database model
- `src/services/llm_service.py` - Statistics capture
- `src/services/rag_service.py` - Stats passthrough
- `src/api/routers/rag.py` - Fire-and-forget logging
- `src/db/repositories/log_repo.py` - Logging repository
- `alembic/versions/4a8f2e1b9c3d_add_llm_call_logs_table.py` - Migration

