import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from flask import request, g
from app.config import Config
from app.core.exceptions import RateLimitExceededError

class RateLimiter:
    """Sliding-window thread-safe in-memory rate limiter per key/IP."""
    def __init__(self):
        # Maps identifier -> list of timestamps (floats)
        self._history: Dict[str, List[float]] = defaultdict(list)
        self._window = Config.RATE_LIMIT_WINDOW_SECONDS
        self._lock = threading.Lock()

    def _cleanup(self, key: str, now: float):
        cutoff = now - self._window
        self._history[key] = [ts for ts in self._history[key] if ts > cutoff]

    def check_rate_limit(self, identifier: str, limit: int) -> Tuple[bool, int, int]:
        """
        Returns (is_allowed, remaining, reset_seconds). Thread-safe atomic check.
        """
        now = time.time()
        with self._lock:
            self._cleanup(identifier, now)
            current_count = len(self._history[identifier])

            if current_count >= limit:
                oldest = self._history[identifier][0] if self._history[identifier] else now
                reset_seconds = max(1, int(self._window - (now - oldest)))
                return False, 0, reset_seconds

            self._history[identifier].append(now)
            remaining = max(0, limit - (current_count + 1))
            reset_seconds = self._window
            return True, remaining, reset_seconds

    def reset(self, identifier: Optional[str] = None):
        """Reset history for a specific identifier or clear all."""
        with self._lock:
            if identifier:
                self._history.pop(identifier, None)
            else:
                self._history.clear()

rate_limiter = RateLimiter()

def apply_rate_limit(tier: str = "free"):
    """
    Hook to check rate limit and append standard HTTP rate limit headers.
    """
    key_info = getattr(g, "api_key_info", None)
    if not key_info:
        from app.core.auth import get_api_key_from_request
        from app.models.storage import db
        api_key = get_api_key_from_request()
        if api_key:
            key_info = db.get_key_info(api_key)
            if key_info:
                g.api_key_info = key_info
                g.api_key = api_key

    if key_info:
        identifier = key_info["key_prefix"]
        key_tier = key_info.get("tier", "free")
    else:
        identifier = request.remote_addr or "anonymous"
        key_tier = tier

    limit = Config.TIER_LIMITS.get(key_tier, Config.TIER_LIMITS["free"])
    is_allowed, remaining, reset_sec = rate_limiter.check_rate_limit(identifier, limit)

    # Attach to g so after_request hook can attach headers to response
    g.rate_limit_headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_sec)
    }

    if not is_allowed:
        raise RateLimitExceededError(
            message=f"Rate limit of {limit} requests/minute exceeded for '{key_tier}' tier.",
            details={
                "tier": key_tier,
                "limit_per_minute": limit,
                "retry_after_seconds": reset_sec
            }
        )
