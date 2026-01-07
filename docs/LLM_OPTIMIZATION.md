# LLM Optimization Guide

## Model Selection

### Comparison Table

| Model | Size | RAM | Speed (tok/s) | Quality | Use Case |
|-------|------|-----|---------------|---------|----------|
| Llama 3.2 1B | 1.3GB | 2GB | 80-100 | Good | Fast inference |
| Llama 3.2 3B | 2.0GB | 3GB | 40-60 | Better | **Selected** |
| Phi-3 Mini | 2.3GB | 3GB | 35-50 | Best/size | Quality focus |

**Selected**: Llama 3.2 3B (Q4_K_M quantization)

### Selection Rationale
- Balance between quality and speed
- Good performance on instruction-following
- Active development and community
- Quantization support

## Optimization Parameters

### Current Configuration
```python
options = {
    "num_ctx": 2048,      # Context window (lower = faster)
    "num_thread": 4,      # CPU threads
    "num_gpu": 99,        # GPU layers (all if available)
    "temperature": 0.7,   # Creativity vs. determinism
    "repeat_penalty": 1.1, # Reduce repetition
    "num_predict": 512,   # Max tokens to generate
}
```

### Parameter Tuning

#### Context Window (num_ctx)
- **Lower (1024)**: Faster, less context
- **Higher (4096)**: Slower, more context
- **Selected (2048)**: Balance for RAG (context in prompt)

#### GPU Offloading (num_gpu)
- **0**: CPU-only (slow but works everywhere)
- **99**: All layers on GPU (fastest if GPU available)
- **Selected (99)**: Maximum performance

#### Temperature
- **0.0**: Deterministic (good for factuality)
- **0.7**: Balanced (selected)
- **1.0+**: Creative (not recommended for RAG)

#### Thread Count (num_thread)
- Match CPU cores
- **Selected (4)**: Good for most systems

## Quantization

### Options
- **F16**: Full precision (best quality, largest)
- **Q8_0**: 8-bit (good quality, smaller)
- **Q4_K_M**: 4-bit medium (selected)
- **Q4_0**: 4-bit (smallest, lower quality)

### Selected: Q4_K_M
- 4x memory reduction
- Minimal quality loss
- Good speed/quality tradeoff

## Benchmarks

### Hardware: [To be filled]
- CPU: [To be filled]
- GPU: [To be filled]
- RAM: [To be filled]

### Performance Metrics

| Configuration | Latency (p50) | Throughput | Memory |
|---------------|---------------|------------|--------|
| Llama 3.2 3B Q4 (CPU) | [To be measured] | [To be measured] | [To be measured] |
| Llama 3.2 3B Q4 (GPU) | [To be measured] | [To be measured] | [To be measured] |

## Optimization Strategies

### 1. Prompt Optimization
- **System Prompt**: Clear, concise instructions
- **Few-shot Examples**: Guide model behavior
- **Context Formatting**: Structured context presentation

### 2. Caching
- Cache common queries
- Cache embeddings
- Cache LLM responses (where appropriate)

### 3. Streaming
- [Future] Stream responses for better UX
- Reduces perceived latency

### 4. Batch Processing
- [Future] Batch multiple queries
- Better GPU utilization

## Production Considerations

### Scaling
- **Horizontal**: Multiple Ollama instances
- **Load Balancing**: Distribute requests
- **Model Replication**: Keep models in memory

### Monitoring
- Latency tracking
- Error rate monitoring
- Token usage tracking
- GPU utilization

### Cost Optimization
- Self-hosted: No per-token cost
- Electricity: ~$0.10-0.50/hour for GPU
- vs. API: $0.10-0.50 per 1K tokens

## Troubleshooting

### Slow Inference
1. Check GPU availability
2. Reduce context window
3. Use lower quantization
4. Reduce num_predict

### High Memory Usage
1. Use quantization (Q4_K_M)
2. Reduce context window
3. Use smaller model (1B)

### Poor Quality
1. Increase temperature slightly
2. Improve prompts
3. Use larger model
4. Increase context window

## Future Optimizations

- [ ] Flash Attention 2
- [ ] vLLM for faster inference
- [ ] Model distillation
- [ ] Custom quantization
- [ ] Hardware-specific optimizations




