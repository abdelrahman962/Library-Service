import json
import time

import redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

# Connect to the local Redis server.
#
# socket_connect_timeout/socket_timeout are deliberately short (same
# value as cache.py's own client): without them, redis-py falls back
# to a long OS-level default when Redis is unreachable — observed to
# take up to ~69 seconds to finally fail — instead of giving up in
# well under a second.
#
# retry: redis.Redis() retries a failed connection attempt by
# default (confirmed empirically — with only the socket timeouts
# above set, a single get() still took ~10s instead of ~0.5s to
# raise). Retry(NoBackoff(), 0) disables that, so a single attempt is
# the whole story: fail in ~0.5s, not ~0.5s times however many
# retries. (Not retry_on_timeout=False — deprecated on this redis-py
# version and unnecessary once `retry` itself is set to 0 retries.)
redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
    retry=Retry(NoBackoff(), 0),
)
CACHE_TTL = 1200


def get_cache(key: str):
    """
    Return the cached value for `key`, or None on a cache miss OR if
    Redis is unreachable for any reason — every tool that calls this
    must keep working (just slower, hitting Laravel directly) when
    Redis is down, same as cache.py's own get_cached().
    """
    start = time.perf_counter()

    try:
        value = redis_client.get(key)
    except RedisError as e:
        elapsed = time.perf_counter() - start
        print(
            f"[REDIS] UNAVAILABLE: {key} "
            f"({elapsed * 1000:.2f} ms) — {e}"
        )
        return None

    elapsed = time.perf_counter() - start

    if value is None:
        print(
            f"[REDIS] CACHE MISS: {key} "
            f"({elapsed * 1000:.2f} ms)"
        )
        return None

    print(
        f"[REDIS] CACHE HIT: {key} "
        f"({elapsed * 1000:.2f} ms)"
    )

    return json.loads(value)


def set_cache(key: str, value, ttl: int = CACHE_TTL):
    """
    Store a value in Redis as JSON. A no-op (not an exception) if
    Redis is unreachable — a failed write here must never crash the
    tool call that already has a real result to return.
    """
    try:
        redis_client.setex(
            key,
            ttl,
            json.dumps(value),
        )
    except RedisError as e:
        print(f"[REDIS] UNAVAILABLE: could not cache {key} — {e}")


def delete_cache(key: str):
    """Delete one cache entry. A no-op if Redis is unreachable."""
    try:
        redis_client.delete(key)
    except RedisError as e:
        print(f"[REDIS] UNAVAILABLE: could not delete {key} — {e}")


def clear_library_cache():
    """
    Delete all library-related cache entries. A no-op if Redis is
    unreachable — a mutation (borrow/return) must still succeed and
    return its result even if the cache it would have invalidated
    can't be reached; the next read will just hit Laravel directly.
    """
    try:
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(
                cursor=cursor,
                match="library:*",
                count=100
            )
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except RedisError as e:
        print(f"[REDIS] UNAVAILABLE: could not clear cache — {e}")
