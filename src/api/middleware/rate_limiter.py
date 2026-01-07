"""Rate limiting middleware."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from collections import defaultdict
import time

from ...core.config import settings
from ...core.logging import setup_logging

logger = setup_logging()

# In-memory rate limiter (swap to Redis in production)
_rate_limiter_store: dict[str, list[float]] = defaultdict(list)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.rate_limit_per_minute
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting if disabled (for load testing)
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        
        # Clean old entries
        current_time = time.time()
        _rate_limiter_store[client_id] = [
            timestamp
            for timestamp in _rate_limiter_store[client_id]
            if current_time - timestamp < 60
        ]
        
        # Check rate limit
        if len(_rate_limiter_store[client_id]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute",
                }
            )
        
        # Add current request
        _rate_limiter_store[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        return response


