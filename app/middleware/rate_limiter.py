# app/middleware/rate_limiter.py
import time
from collections import defaultdict, deque
from typing import Dict, Deque

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm."""

    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)

        self.last_cleanup = time.time()
        self.cleanup_interval = 300

    async def dispatch(self, request: Request, call_next):
        if self._should_skip_rate_limiting(request):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = time.time()

        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_requests(current_time)
            self.last_cleanup = current_time

        if self._is_rate_limited(client_ip, current_time):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"}
            )

        self.requests[client_ip].append(current_time)

        return await call_next(request)

    @classmethod
    def _should_skip_rate_limiting(cls, request: Request) -> bool:
        """Skip rate limiting for certain endpoints."""
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/ping"
        ]
        return any(request.url.path.startswith(path) for path in skip_paths)

    @classmethod
    def _get_client_ip(cls, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded rate limits."""
        requests = self.requests[client_ip]

        while requests and current_time - requests[0] > 3600:
            requests.popleft()

        if len(requests) >= self.requests_per_hour:
            return True

        recent_requests = sum(1 for req_time in requests if current_time - req_time < 60)
        if recent_requests >= self.requests_per_minute:
            return True

        return False

    def _cleanup_old_requests(self, current_time: float):
        """Remove old request records to prevent memory leaks."""
        for client_ip in list(self.requests.keys()):
            requests = self.requests[client_ip]

            while requests and current_time - requests[0] > 3600:
                requests.popleft()

            if not requests:
                del self.requests[client_ip]
