# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""Redis caching utility — transparent layer with in-memory fallback."""
import os
import json
import hashlib
import logging

logger = logging.getLogger("cache")

# Connect to Redis (fallback to in-memory dict if Redis unavailable)
REDIS_URL = os.getenv("REDIS_URL")
_redis = None
_fallback = {}  # in-memory fallback


def get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if REDIS_URL:
        try:
            import redis
            _redis = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
            _redis.ping()
            logger.info(f"Redis connected: {REDIS_URL[:30]}...")
            return _redis
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
            _redis = None
    return None


def _make_key(prefix: str, *args, **kwargs) -> str:
    raw = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"sam:{prefix}:{h}"


def cache_get(prefix: str, *args, **kwargs):
    key = _make_key(prefix, *args, **kwargs)
    r = get_redis()
    if r:
        try:
            val = r.get(key)
            if val:
                return json.loads(val)
        except Exception:
            pass
    else:
        entry = _fallback.get(key)
        if entry:
            import time
            if time.time() < entry["exp"]:
                return entry["val"]
            del _fallback[key]
    return None


def cache_set(prefix: str, value, ttl: int, *args, **kwargs):
    key = _make_key(prefix, *args, **kwargs)
    r = get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass
    else:
        import time
        _fallback[key] = {"val": value, "exp": time.time() + ttl}


def cache_clear(prefix: str = None):
    """Clear cache entries. If prefix given, clear only matching keys."""
    r = get_redis()
    if r:
        try:
            if prefix:
                keys = r.keys(f"sam:{prefix}:*")
            else:
                keys = r.keys("sam:*")
            if keys:
                r.delete(*keys)
        except Exception:
            pass
    else:
        if prefix:
            to_del = [k for k in _fallback if k.startswith(f"sam:{prefix}:")]
            for k in to_del:
                del _fallback[k]
        else:
            _fallback.clear()
