"""
Keyword-based route classifier — retained as a safety-net fallback.

This is the original substring/keyword classifier that used to be
`router.route_request()`. It no longer runs on the normal request
path; `ai_router.classify_route()` calls into this module only when
the LLM router's output cannot be parsed into a valid group.

Kept here (rather than deleted) so routing never has a hard failure
mode: if the AI router is unavailable or returns garbage, the
assistant still degrades gracefully to deterministic keyword matching
instead of erroring out.
"""

from typing import Literal

ToolGroup = Literal[
    "books",
    "user",
    "borrowing",
    "admin",
    "general",
]


def route_request(user_message: str) -> ToolGroup:
    """
    Determine which specialized agent should handle the request,
    using plain keyword/substring matching.
    """

    text = user_message.lower().strip()

    # =====================================================
    # USER
    # =====================================================

    user_keywords = [
        "my profile",
        "my account",
        "my borrowed",
        "what have i borrowed",
        "what did i borrow",
        "my borrowing",
        "my history",
        "my borrow history",
        "books i borrowed",
        "books i've borrowed",
        "books that i borrowed",
    ]

    if any(keyword in text for keyword in user_keywords):
        return "user"

    # =====================================================
    # BORROWING
    # =====================================================

    borrowing_keywords = [
        "borrow ",
        "return ",
        "give back ",
        "take out ",
        "check out ",
    ]

    if any(keyword in text for keyword in borrowing_keywords):
        return "borrowing"

    # =====================================================
    # ADMIN / HISTORY
    # =====================================================

    admin_keywords = [
        "library stats",
        "library statistics",
        "statistics",
        "stats",
        "list members",
        "member list",
    ]

    if any(keyword in text for keyword in admin_keywords):
        return "admin"

    # =====================================================
    # BORROWING HISTORY
    # =====================================================

    if "borrowing history" in text or "borrow history" in text:
        return "admin"

    # =====================================================
    # BOOKS
    # =====================================================

    book_keywords = [
        "book",
        "books",
        "available",
        "author",
        "title",
        "category",
        "show all",
        "list all",
        "information about",
        "details about",
        "search",
        "find",
    ]

    if any(keyword in text for keyword in book_keywords):
        return "books"

    # =====================================================
    # GENERAL
    # =====================================================

    return "general"
