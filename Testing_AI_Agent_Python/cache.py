"""
Lightweight Redis-backed cache for read-only library tool calls.

Why: several tools (library_stats, list_all_books, my_borrowed_books,
...) hit the Laravel API fresh on every single call, even when the
exact same call was just made seconds ago — the same question asked
twice, or the same tool called twice within one multi-part request.
A short-TTL cache, keyed by (tool name, arguments) rather than
anything the user typed, skips that redundant round-trip without ever
inspecting user text — see tools.py's docstrings for the "no keyword
routing" constraint this is designed to respect: caching decisions are
made purely on the structured tool call the model already chose to
make, never on the request that led to it.

Cache is invalidated wholesale (not per-key) whenever a borrow_book/
return_book call succeeds, since a single borrow/return can affect
many different tools' results (stats, availability, borrowed-books
lists, borrow histories, member records) — flushing everything is
simpler and safer than trying to enumerate exactly which keys a given
mutation could have staled.

Redis is treated as fully optional infrastructure: if it isn't
running, every cache operation fails silently and tools just call the
real API every time, exactly as they did before this existed. Nothing
about the agent's correctness depends on Redis being up — only its
speed on repeated calls.
"""

import hashlib
import json
from typing import Any, Callable

import redis

# Deliberately short: this is a "skip an identical call made moments
# ago" cache, not a general-purpose data store. Long-lived caching of
# library data (which can change any time someone borrows/returns a
# book) would risk showing stale state — the whole point of keeping
# this short is that staleness is bounded to a few seconds even if
# invalidation somehow missed something.
_TTL_SECONDS = 300

_NAMESPACE = "library_agent_cache"

try:
    # protocol=2: Laragon's bundled Redis is 5.0.14, which predates
    # RESP3 (Redis 6+) — the modern redis-py client defaults to
    # negotiating RESP3 via a HELLO command this server doesn't
    # support, so this has to be pinned explicitly (see this
    # session's own HELLO ResponseError for why).
    _client: redis.Redis | None = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True,
        protocol=2,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )
    _client.ping()
except Exception:
    _client = None


def get_client() -> redis.Redis | None:
    """
    Expose this module's own Redis connection (or None if Redis isn't
    reachable) so other modules — memory.py in particular — reuse the
    same protocol=2-pinned client instead of opening a second
    connection with the RESP3-negotiation problem described above.
    """
    return _client


def _key(tool_name: str, args: dict[str, Any]) -> str:
    # Sorted-key JSON so the same arguments always hash to the same
    # key regardless of dict insertion order.
    args_json = json.dumps(args, sort_keys=True, default=str)
    digest = hashlib.sha256(args_json.encode()).hexdigest()[:16]
    return f"{_NAMESPACE}:{tool_name}:{digest}"


def get_cached(tool_name: str, args: dict[str, Any]) -> Any | None:
    """
    Return a previously cached value for this exact (tool_name, args),
    or None on a miss / Redis being unavailable. Split out of
    cached_call so a caller that needs to decide WHETHER a result is
    safe to cache (e.g. streamlit_app.py's response cache, which must
    never cache a turn that ran a mutating tool) can check for a hit
    without being forced to also write on every miss.
    """
    if _client is None:
        return None
    key = _key(tool_name, args)
    try:
        cached = _client.get(key)
        return json.loads(cached) if cached is not None else None
    except Exception:
        return None


def set_cached(tool_name: str, args: dict[str, Any], result: Any) -> None:
    """
    Store `result` under this exact (tool_name, args) for _TTL_SECONDS.
    See get_cached above for why this is separate from cached_call.
    """
    if _client is None:
        return
    key = _key(tool_name, args)
    try:
        _client.setex(key, _TTL_SECONDS, json.dumps(result, default=str))
    except Exception:
        pass


def cached_call(tool_name: str, args: dict[str, Any], fetch: Callable[[], Any]) -> Any:
    """
    Return fetch()'s result, reusing a cached copy if one was stored
    under this exact (tool_name, args) within the last _TTL_SECONDS.
    Falls back to calling fetch() directly — no caching, but no
    breakage either — if Redis is unavailable for any reason.
    """
    cached = get_cached(tool_name, args)
    if cached is not None:
        return cached

    result = fetch()
    set_cached(tool_name, args, result)
    return result


def invalidate_all() -> None:
    """
    Flush every cached tool result. Call this after a borrow_book/
    return_book succeeds — see module docstring for why it's a full
    flush rather than a targeted one.
    """
    if _client is None:
        return
    try:
        for key in _client.scan_iter(f"{_NAMESPACE}:*"):
            _client.delete(key)
    except Exception:
        pass
