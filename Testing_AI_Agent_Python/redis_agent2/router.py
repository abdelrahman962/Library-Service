"""
Deterministic request resolution.

This module no longer classifies intent (that's ai_router.py, with
router_keyword_backup.py as its fallback). What's left here is
strictly deterministic: exact-phrase fast paths, borrowing-history
target extraction/resolution, and the ToolGroup type shared across
the routing modules.
"""

from typing import Literal
import re

ToolGroup = Literal[
    "books",
    "user",
    "borrowing",
    "admin",
    "general",
]


# =========================================================
# Direct tool -> group label
# =========================================================
#
# A 1:1 lookup used only to label an already-resolved direct tool
# with its owning group (e.g. for the Streamlit "Route:" caption).
# This is not intent classification - by the time it's consulted,
# get_direct_tool() or resolve_history_tool() has already decided
# exactly which tool will run.

DIRECT_TOOL_GROUP: dict[str, ToolGroup] = {
    "my_profile": "user",
    "my_borrowed_books": "user",
    "my_borrow_history": "user",

    "list_members": "admin",
    "library_stats": "admin",
    "book_borrow_history": "admin",
    "member_borrow_history": "admin",

    "list_all_books": "books",
    "list_available_books": "books",
    "list_borrowed_books": "books",
}


def get_direct_tool(user_message: str) -> str | None:
    """
    Return the exact tool name for simple, unambiguous requests.

    Returns None when the request requires LLM/tool reasoning.
    """

    text = user_message.lower().strip()

    # =====================================================
    # USER
    # =====================================================

    if text in {
        "my profile",
        "show my profile",
        "show my account",
        "my account",
    }:
        return "my_profile"

    if text in {
        "what have i borrowed",
        "what have i borrowed?",
        "my borrowed books",
        "show my borrowed books",
        "what books have i borrowed",
        "what books have i borrowed?",
    }:
        return "my_borrowed_books"

    if text in {
        "my borrowing history",
        "show my borrowing history",
        "my borrow history",
        "show my borrow history",
    }:
        return "my_borrow_history"

    # =====================================================
    # ADMIN
    # =====================================================

    if text in {
        "list members",
        "show members",
        "show all members",
        "member list",
        "list all members",
    }:
        return "list_members"

    if text in {
        "library stats",
        "library statistics",
        "show library stats",
        "show library statistics",
        "statistics",
        "stats",
    }:
        return "library_stats"

    # =====================================================
    # BOOKS
    # =====================================================

    if text in {
        "show all books",
        "show all the books",
        "list all books",
        "list all the books",
    }:
        return "list_all_books"

    if text in {
        "show available books",
        "show available",
        "list available books",
        "list available",
    }:
        return "list_available_books"

    if text in {
        "show borrowed books",
        "list borrowed books",
        "show all borrowed books",
        "list all borrowed books",
    }:
        return "list_borrowed_books"

    # =====================================================
    # No deterministic match
    # =====================================================

    return None



def extract_history_target(user_message: str) -> str | None:
    """
    Extract the person/book name from requests such as:

        show Omar borrowing history
        show Sapiens borrowing history
        Omar borrow history
        Sapiens borrowing history
    """

    patterns = [
        r"^(?:show|get|find|display)\s+(.+?)\s+(?:borrowing|borrow)\s+history$",
        r"^(.+?)\s+(?:borrowing|borrow)\s+history$",
    ]

    for pattern in patterns:
        match = re.match(
            pattern,
            user_message.strip(),
            re.IGNORECASE,
        )

        if match:
            target = match.group(1).strip()

            if target:
                return target

    return None


def resolve_history_tool(
    user_message: str,
    api_client,
) -> tuple[str, str] | None:

    """
    Determine whether a borrowing-history request refers
    to a member or a book.

    Returns:

        ("member_borrow_history", target)

    or:

        ("book_borrow_history", target)

    or None if the request is not a history request.

    Raises ValueError when the target cannot be resolved
    safely or is ambiguous.
    """

    target = extract_history_target(user_message)

    # -----------------------------------------------------
    # Not a history request
    # -----------------------------------------------------

    if target is None:
        return None

    # -----------------------------------------------------
    # Search for member
    # -----------------------------------------------------

    member_matches = []

    try:
        member_result = api_client.list_members(
            target,
            1,
        )

        member_matches = (
            member_result
            .get("data", {})
            .get("data", [])
        )

    except Exception:
        member_matches = []

    # -----------------------------------------------------
    # Search for book
    # -----------------------------------------------------

    book_matches = []

    try:
        book_result = api_client.search_books(
            target
        )

        book_matches = (
            book_result
            .get("data", [])
        )

    except Exception:
        book_matches = []

    # -----------------------------------------------------
    # Exactly one member
    # -----------------------------------------------------

    if len(member_matches) == 1 and len(book_matches) == 0:

        return (
            "member_borrow_history",
            target,
        )

    # -----------------------------------------------------
    # Exactly one book
    # -----------------------------------------------------

    if len(book_matches) == 1 and len(member_matches) == 0:

        return (
            "book_borrow_history",
            target,
        )

    # -----------------------------------------------------
    # Nothing found
    # -----------------------------------------------------

    if not member_matches and not book_matches:

        raise ValueError(
            f"No member or book found matching {target!r}."
        )

    # -----------------------------------------------------
    # Multiple members
    # -----------------------------------------------------

    if len(member_matches) > 1:

        options = ", ".join(
            f"{member.get('name')} "
            f"(ID {member.get('id')})"
            for member in member_matches
        )

        raise ValueError(
            f"Multiple members match {target!r}: "
            f"{options}. "
            f"Please specify the member more clearly."
        )

    # -----------------------------------------------------
    # Multiple books
    # -----------------------------------------------------

    if len(book_matches) > 1:

        options = ", ".join(
            f"{book.get('title')} "
            f"(ID {book.get('id')})"
            for book in book_matches
        )

        raise ValueError(
            f"Multiple books match {target!r}: "
            f"{options}. "
            f"Please specify the book more clearly."
        )

    # -----------------------------------------------------
    # Both a member and book matched
    # -----------------------------------------------------

    raise ValueError(
        f"{target!r} matches both a member and a book. "
        f"Please specify whether you mean the member "
        f"or the book."
    )
