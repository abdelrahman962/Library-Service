"""
AI-based route classifier.

Replaces keyword/substring intent classification with an LLM call.
This module has exactly one job: given the current user message,
decide which specialized agent group should handle it. It never
executes tools and never sees conversation history — both by design,
to keep routing fast, narrow, and side-effect free.

Deterministic concerns stay out of this file on purpose:

    - Exact-phrase fast paths            -> router.get_direct_tool()
    - Borrowing-history target resolution -> router.resolve_history_tool()

Those are handled before this module is ever consulted (see
routed_agent.invoke_routed_agent), so classify_route() only runs for
requests that didn't already resolve to a deterministic tool.
"""

import os
import sys
from pathlib import Path
from typing import Literal, Optional, cast

from langchain_ollama import ChatOllama

# =========================================================
# Project root
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# Project imports
# =========================================================

try:
    from .router import ToolGroup
except ImportError:
    from router import ToolGroup

try:
    from .router_keyword_backup import route_request as _keyword_route_request
except ImportError:
    from router_keyword_backup import route_request as _keyword_route_request


# =========================================================
# Valid AI-routable categories
# =========================================================
#
# "general" is intentionally NOT part of this set. The model is
# never told about it - it is only what the keyword fallback returns
# when a request genuinely matches nothing else.
#
# AiRoute is a subset of ToolGroup's literals, so a value typed
# AiRoute is always safely assignable where ToolGroup is expected.

AiRoute = Literal[
    "books",
    "user",
    "borrowing",
    "admin",
]

AI_ROUTES: set[AiRoute] = {
    "books",
    "user",
    "borrowing",
    "admin",
}


# Tolerant synonyms for the natural words a small model tends to
# reach for even when told the exact category name. Keeps genuinely
# on-topic answers from being thrown away and sent to the (slower)
# keyword fallback just because of wording.
AI_ROUTE_SYNONYMS: dict[str, AiRoute] = {
    "book": "books",
    "borrow": "borrowing",
    "borrowed": "borrowing",
    "return": "borrowing",
    "returning": "borrowing",
    "profile": "user",
    "account": "user",
    "users": "user",
    "administration": "admin",
    "administrative": "admin",
    "statistics": "admin",
    "stats": "admin",
    "member": "admin",
    "members": "admin",
}


# =========================================================
# Router prompt
# =========================================================
#
# Loaded once at import time from prompts/router.md - not re-read
# per request.

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


ROUTER_SYSTEM_PROMPT = _load_prompt("router.md")


# =========================================================
# Lazily-created router model
# =========================================================
#
# Same model tag as the group agents (so Ollama keeps a single
# instance warm), but its own ChatOllama instance tuned for a
# one-word answer instead of a full agent turn.

_router_model: Optional[ChatOllama] = None


def _get_router_model() -> ChatOllama:

    global _router_model

    if _router_model is None:

        _router_model = ChatOllama(
            model=os.getenv(
                "OLLAMA_MODEL",
                "qwen3:1.7b",
            ),
            temperature=0,
            reasoning=False,
            keep_alive="30m",
            num_predict=10,
        )

    return _router_model


# =========================================================
# Response parsing
# =========================================================

def _parse_route(raw: str) -> Optional[AiRoute]:
    """
    Normalize the model's reply and check it against AI_ROUTES.

    Returns None when the reply doesn't cleanly resolve to one of
    the four AI-routable categories.
    """

    if not raw:
        return None

    candidate = raw.strip().lower().strip(" .!?\"'`\n\t")

    if candidate in AI_ROUTES:
        return cast(AiRoute, candidate)

    if candidate in AI_ROUTE_SYNONYMS:
        return AI_ROUTE_SYNONYMS[candidate]

    # Tolerate a stray leading/trailing word around the category,
    # e.g. "books." or a short sentence despite num_predict=10.
    words = candidate.split()

    for word in words:

        word = word.strip(" .!?\"'`\n\t,:;")

        if word in AI_ROUTES:
            return cast(AiRoute, word)

        if word in AI_ROUTE_SYNONYMS:
            return AI_ROUTE_SYNONYMS[word]

    return None


# =========================================================
# Public entry point
# =========================================================

def classify_route(user_message: str) -> ToolGroup:
    """
    Ask the LLM which group should handle this request.

    Receives only the current user message - no conversation
    history - so routing stays fast and narrowly scoped.

    Falls back to the deterministic keyword router
    (router_keyword_backup.route_request) if the model is
    unreachable or returns something that doesn't parse into one
    of the four AI-routable groups, so routing never hard-fails.
    """

    try:

        model = _get_router_model()

        response = model.invoke(
            [
                {
                    "role": "system",
                    "content": ROUTER_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ]
        )

        raw = getattr(response, "content", "")

        if not isinstance(raw, str):
            raw = str(raw)

        route = _parse_route(raw)

        if route is not None:
            return route

        print(
            f"[AI_ROUTER] Unparseable response {raw!r}; "
            f"falling back to keyword router."
        )

    except Exception as e:

        print(
            f"[AI_ROUTER] Error calling router model ({e}); "
            f"falling back to keyword router."
        )

    return _keyword_route_request(user_message)
