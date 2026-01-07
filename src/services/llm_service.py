"""LLM service for Ollama integration."""
import httpx
import asyncio
from typing import Optional, Dict, Any, Tuple
import json
import time

from ..core.config import settings
from ..core.logging import setup_logging
from ..core.exceptions import LLMError

logger = setup_logging()


class LLMService:
    """Service for interacting with Ollama LLM."""
    
    def __init__(self, max_concurrent_requests: int = 5):
        """
        Initialize LLM service.
        
        Args:
            max_concurrent_requests: Maximum concurrent requests to Ollama (default: 5)
                                     This prevents overwhelming Ollama under high load
        """
        self.base_url = settings.ollama_base_url
        self.model = settings.llm_model
        # Increased timeout for high load scenarios
        self.client = httpx.AsyncClient(timeout=180.0, limits=httpx.Limits(max_connections=10, max_keepalive_connections=5))
        # Semaphore to limit concurrent requests to Ollama
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial retry delay in seconds
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text using Ollama and return statistics.
        
        Returns:
            Tuple of (content, stats_dict) where stats_dict contains:
            - model_name: Model used
            - latency_ms: LLM processing time
            - queue_wait_ms: Time waiting in semaphore
            - prompt_tokens: Input tokens (if available)
            - completion_tokens: Output tokens (if available)
            - total_tokens: Total tokens (if available)
            - temperature: Temperature parameter
            - max_tokens: Max tokens parameter
            - retry_attempts: Number of retries
        
        Optimizations applied:
        - num_ctx: 2048 (lower context = faster)
        - num_gpu: 99 (full GPU offload if available)
        - Q4_K_M quantization (4x memory reduction)
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": 1024,   # Reduced context window for speed (1024 vs 2048)
                "num_thread": 4,   # CPU threads
                "num_gpu": 99,     # GPU layers (all if available)
                "repeat_penalty": 1.1,
                "top_k": 40,       # Reduce top_k for faster sampling
                "top_p": 0.9,      # Nucleus sampling for faster generation
            },
            **kwargs,
        }
        
        # Track queue wait time (minimal overhead: <1μs)
        queue_start = time.time()
        
        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            queue_wait_ms = int((time.time() - queue_start) * 1000)
            
            # Retry logic with exponential backoff
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    # Track LLM processing time (minimal overhead: <1μs)
                    llm_start = time.time()
                    
                    response = await self.client.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    llm_latency_ms = int((time.time() - llm_start) * 1000)
                    content = result.get("message", {}).get("content", "")
                    
                    if not content:
                        logger.warning(f"Empty response from LLM on attempt {attempt + 1}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        raise LLMError("Empty response from LLM")
                    
                    # Extract token statistics from Ollama response (already parsed, just extract)
                    prompt_tokens = result.get("prompt_eval_count")
                    completion_tokens = result.get("eval_count")
                    total_tokens = None
                    if prompt_tokens is not None and completion_tokens is not None:
                        total_tokens = prompt_tokens + completion_tokens
                    
                    # Build statistics dict (minimal overhead: <1μs)
                    stats = {
                        "model_name": self.model,
                        "latency_ms": llm_latency_ms,
                        "queue_wait_ms": queue_wait_ms,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "retry_attempts": attempt,
                    }
                    
                    return content, stats
                    
                except httpx.TimeoutException as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"LLM request timeout (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(f"LLM request timeout after {self.max_retries} attempts: {e}")
                    # Return error stats before raising
                    stats = {
                        "model_name": self.model,
                        "latency_ms": 0,
                        "queue_wait_ms": queue_wait_ms,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "retry_attempts": attempt,
                        "success": False,
                        "error_message": f"Timeout after {self.max_retries} attempts",
                    }
                    raise LLMError(f"LLM request timeout after {self.max_retries} attempts: {e}")
                    
                except httpx.HTTPStatusError as e:
                    last_error = e
                    # Don't retry on client errors (4xx)
                    if 400 <= e.response.status_code < 500:
                        logger.error(f"LLM client error: {e.response.status_code} - {e.response.text}")
                        raise LLMError(f"LLM client error: {e.response.status_code}")
                    # Retry on server errors (5xx)
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"LLM server error {e.response.status_code} (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(f"LLM server error after {self.max_retries} attempts: {e.response.status_code}")
                    raise LLMError(f"LLM server error: {e.response.status_code}")
                    
                except httpx.HTTPError as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"LLM request failed (attempt {attempt + 1}/{self.max_retries}): {e}, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(f"LLM request failed after {self.max_retries} attempts: {e}")
                    raise LLMError(f"Failed to generate response after {self.max_retries} attempts: {e}")
                    
                except Exception as e:
                    last_error = e
                    logger.error(f"Unexpected error in LLM request: {e}", exc_info=True)
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    raise LLMError(f"Unexpected error: {e}")
            
            # If we get here, all retries failed
            raise LLMError(f"Failed to generate response after {self.max_retries} attempts: {last_error}")
    
    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


