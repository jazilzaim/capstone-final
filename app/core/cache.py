import time
import threading
import logging
from typing import Any, Optional, Dict, Tuple
from app.config import Config

logger = logging.getLogger("argus.core.cache")

class CacheEntry:
    __slots__ = ("data", "expires_at")
    def __init__(self, data: Any, expires_at: float):
        self.data = data
        self.expires_at = expires_at

class MemoryCache:
    """Production-grade thread-safe in-memory cache with TTL and capacity bounds."""
    def __init__(self, max_entries: int = Config.CACHE_MAX_ENTRIES):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_entries = max_entries
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def _make_key(self, prefix: str, **params) -> str:
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
        return f"{prefix}:{param_str}"

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if entry.expires_at > now:
                    self.hits += 1
                    return entry.data
                else:
                    # Expired entry cleanup
                    del self._cache[key]
            self.misses += 1
            return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        ttl = ttl if ttl is not None else Config.CACHE_DEFAULT_TTL_SECONDS
        now = time.time()
        with self._lock:
            # If at max capacity and inserting a new key, evict expired or lowest expires_at
            if key not in self._cache and len(self._cache) >= self._max_entries:
                # First check for any already expired keys to purge
                expired_keys = [k for k, v in self._cache.items() if v.expires_at <= now]
                if expired_keys:
                    for k in expired_keys[:10]:
                        del self._cache[k]
                else:
                    oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].expires_at)
                    del self._cache[oldest_key]

            self._cache[key] = CacheEntry(data, now + ttl)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self.hits + self.misses
            hit_ratio = round((self.hits / total * 100) if total > 0 else 0.0, 1)
            return {
                "entries_count": len(self._cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio_percent": hit_ratio
            }

    def warm_cache(self, registry=None):
        """Warm up cache with baseline municipal datasets on startup."""
        if not registry:
            try:
                from app.connectors.registry import registry
            except Exception as e:
                logger.warning(f"Could not import registry for cache warmup: {e}")
                return

        logger.info("Priming cache with baseline municipal datasets across 4 cities...")
        try:
            # Warm incidents
            incidents_key = self._make_key("incidents", city="all", category=None, q=None, lim=20, off=0)
            raw_incidents = registry.query_incidents(city="all", limit=20)
            self.set(incidents_key, [i.to_dict() for i in raw_incidents])

            # Warm permits
            permits_key = self._make_key("permits", city="all", q=None, ptype=None, lim=20, off=0)
            raw_permits = registry.query_permits(city="all", limit=20)
            self.set(permits_key, [p.to_dict() for p in raw_permits])

            # Warm businesses
            biz_key = self._make_key("businesses", city="all", q=None, cat=None, lim=20, off=0)
            raw_biz = registry.query_businesses(city="all", limit=20)
            self.set(biz_key, [b.to_dict() for b in raw_biz])

            # Warm cities info
            cities_key = "cities:all"
            self.set(cities_key, [c.to_dict() for c in registry.get_all_cities_info()])

            logger.info(f"Cache successfully warmed. Current entries: {len(self._cache)}")
        except Exception as e:
            logger.warning(f"Cache warmup encountered a non-fatal error: {e}")

cache = MemoryCache()
