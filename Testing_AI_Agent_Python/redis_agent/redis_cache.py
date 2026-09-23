import json
import redis

# Connect to the local Redis server
redis_client = redis.Redis(
     host="127.0.0.1",
    port=6379,
    db=0,
    decode_responses=True,
)
CACHE_TTL =600

def get_cache(key: str):
    import time

    start = time.perf_counter()

    value = redis_client.get(key)

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
def set_cache(key: str, value, ttl: int =CACHE_TTL):
    """Store a value in Redis as JSON"""
    redis_client.setex(
        key,
        ttl,
        json.dumps(value),
    )

def delete_cache(key: str):
    """Delete one cache entry."""

    redis_client.delete(key)


def clear_library_cache():
    """Delete all library-related cache entries."""
    cursor = 0
    while True:
        cursor, keys =redis_client.scan(
            cursor=cursor,
            match ="library:*",
            count=100
        )
        if keys:
            redis_client.delete(*keys)
        if cursor == 0:
            break
