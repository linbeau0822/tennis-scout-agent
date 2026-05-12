from __future__ import annotations

import json
from typing import Optional

import redis

from app.config import get_settings

settings = get_settings()

_client: Optional[redis.Redis] = None
_initialized = False


def _get_client() -> Optional[redis.Redis]:
    global _client, _initialized
    if _initialized:
        return _client

    _initialized = True
    if not settings.llm_cache_enabled or not settings.redis_url:
        return None

    try:
        _client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
    except Exception as e:
        print(f"Redis client init failed: {e}. Cache disabled for this process.")
        _client = None
    return _client


def cache_status() -> str:
    return "enabled" if _get_client() is not None else "disabled"


def cache_get_json(key: str) -> Optional[dict]:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        print(f"Redis GET failed for key={key!r}: {e}")
        return None


def cache_set_json(key: str, value: dict, ttl_seconds: int) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception as e:
        print(f"Redis SET failed for key={key!r}: {e}")


def ping_cache() -> bool:
    client = _get_client()
    if client is None:
        print("Redis cache disabled (no REDIS_URL or feature flag off).")
        return False
    try:
        client.ping()
        print(f"Redis cache enabled at {settings.redis_url}.")
        return True
    except Exception as e:
        print(f"Redis ping failed: {e}. Cache will be skipped at runtime.")
        return False
