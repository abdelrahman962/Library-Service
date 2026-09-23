"""
Same tools as ../tools.py, but with no caching layer at all — every
call goes straight to the Laravel API every time, no Redis involved.

Kept as a fully separate file (its own module-level `api` singleton,
its own copies of every tool) rather than a flag on tools.py, so this
version and the Redis-backed one can run side by side as completely
independent agent/Streamlit pairs without one affecting the other.
"""

import os
import sys
from typing import Any

from langchain_core.tools import tool

# api_client.py lives one level up (Testing_AI_Agent_Python/), shared
# across every agent folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import LibraryAPIClient, LibraryAPIError


# Create one API client that all tools will use
api = LibraryAPIClient()


# ============================================================
# BOOK TOOLS
# ============================================================

@tool
def search_books(search: str) -> dict[str, Any]:
    """
    Search for books by title, author, or category.

    Use this tool when the user wants to find a specific book
    or books matching a keyword.
    """
    try:
        return api.search_books(search)

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def list_available_books() -> dict[str, Any]:
    """
    List all books that are currently available for borrowing.
    """
    try:
        return api.available_books()

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def list_borrowed_books() -> dict[str, Any]:
    """
    List every book that is currently borrowed, with who borrowed
    each one. Use this — not list_all_books — when the user asks to
    see just the borrowed books (e.g. "show all borrowed books",
    "what's currently checked out"): this is filtered server-side to
    borrowed books only, rather than requiring you to look at
    list_all_books' full result and work out which ones are borrowed
    yourself.
    """
    try:
        return api.borrowed_books()

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def list_all_books() -> dict[str, Any]:
    """
    List all books in the library.
    """
    try:
        return api.all_books()

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def get_book_details(book_id: int) -> dict[str, Any]:
    """
    Get detailed information about a specific book by its ID.
    """
    try:
        return api.get_book(book_id)

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================
# MEMBER TOOLS
# ============================================================

@tool
def my_profile() -> dict[str, Any]:
    """
    Get the currently authenticated member's own profile: name,
    email, and whether they're an admin. Use this when the user asks
    about their own identity or account (e.g. "what's my name",
    "what's my email", "am I an admin") — never guess or reuse a
    name/email mentioned earlier in the conversation for this; call
    this tool fresh each time.
    """
    try:
        return api.get_current_user()

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def my_borrowed_books() -> dict[str, Any]:
    """
    List the books currently borrowed by the authenticated member.

    The authenticated member is determined by the Laravel
    Sanctum token. Do not ask the user for their member ID.
    """
    try:
        return api.my_borrowed_books()

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def my_borrow_history() -> dict[str, Any]:
    """
    Show the borrowing history of the authenticated member.

    The authenticated member is determined by the Laravel
    Sanctum token.
    """
    try:
        return api.my_borrow_history()

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================
# BORROW / RETURN TOOLS
# ============================================================

@tool
def borrow_book(book: str) -> dict[str, Any]:
    """
    Borrow a book. `book` may be a numeric book ID or a title/keyword
    to search for — pass along whatever the user gave you as-is; this
    tool resolves it internally, so do not call search_books
    yourself first. (Resolving it yourself, in a separate step, is
    exactly what caused a real, wrong book to get borrowed/returned
    instead of the one asked for — see member_borrow_history/
    book_borrow_history for the same reasoning.)

    The book is borrowed by the currently authenticated member.
    Do not ask the user for a member ID or member email.
    """
    try:
        book_id = _resolve_book_id(book)
        return api.borrow_book(book_id)

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def return_book(book: str) -> dict[str, Any]:
    """
    Return a book. `book` may be a numeric book ID or a title/keyword
    to search for — pass along whatever the user gave you as-is; this
    tool resolves it internally, so do not call search_books
    yourself first. (Resolving it yourself, in a separate step, is
    exactly what caused a real, wrong book to get returned instead of
    the one asked for.)

    The book is returned by the currently authenticated member.
    Do not ask the user for a member ID or member email.
    """
    try:
        book_id = _resolve_book_id(book)
        return api.return_book(book_id)

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================
# MEMBERS (admin only)
# ============================================================

@tool
def list_members(search: str = "") -> dict[str, Any]:
    """
    List every library member and their currently borrowed books —
    admin accounts only.

    Optionally filter by `search` (matches member name or email) to
    look up a specific member.

    If the authenticated user is not an admin, the API rejects this
    and the tool returns an error explaining that — do not retry it
    or ask the user for admin credentials, just relay the error.
    """
    try:
        # The underlying endpoint paginates at 5/page (sized for the
        # admin web UI), but a library has, realistically, at most a
        # few dozen members — there's no reason a chat tool should
        # ever hand back a partial list, so fetch every page
        # ourselves rather than exposing pagination to the model at
        # all (a capped loop, not "while True", so a bug in the API
        # can't hang this on a runaway loop).
        members = []
        last_page = 1
        page = 1
        while page <= last_page and page <= 20:
            result = api.list_members(search or None, page)
            paginator = result.get("data", {})
            members.extend(paginator.get("data", []))
            last_page = paginator.get("last_page", page)
            page += 1

        # Drop each member's hashed password: the raw API response
        # includes it (a pre-existing gap in the Laravel app —
        # Member has no $hidden — unrelated to this tool), and
        # there's no reason for that to ever enter the model's
        # context or get echoed into a chat transcript.
        return {
            "success": True,
            "data": [
                {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "email": m.get("email"),
                    "is_admin": m.get("is_admin"),
                    "borrowed_books_count": len(m.get("books") or []),
                    "borrowed_books": [
                        {"id": b.get("id"), "title": b.get("title")}
                        for b in (m.get("books") or [])
                    ],
                }
                for m in members
            ],
            # Named to stay accurate whether or not `search` was
            # used: "matching" when filtering, "in the library" when
            # not — a bare "total" here would misleadingly read as
            # the whole library's member count even when this is
            # really just a search result (e.g. searching "omar"
            # returning 1 must never be read as "the library has 1
            # member").
            "count": len(members),
            "count_meaning": (
                f"members matching search {search!r}" if search
                else "total members in the library"
            ),
        }

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================
# BORROW HISTORY (admin only)
# ============================================================

# Both history tools below take a name/title OR a numeric ID and
# resolve it internally, rather than requiring the model to call
# list_members/search_books itself first in a separate turn. That
# two-step "resolve, then remember the ID for the next call" pattern
# is exactly what qwen3:1.7b was observed to get wrong repeatedly:
# guessing/reusing a stale ID from earlier in the conversation instead
# of doing a fresh lookup. Doing the resolution here, in plain Python,
# removes the failure mode structurally instead of relying on prompt
# wording — this is ordinary parameter normalization inside a tool
# the model has already chosen to call, not text-based routing.

def _resolve_member_id(member: str) -> int:
    """
    Resolve a numeric ID or a name/email into a member ID.

    Raises LibraryAPIError (same as every other lookup here) when
    there's no match or more than one — the caller's existing
    `except LibraryAPIError` handles it, so a resolver can never
    hand back an ambiguous/missing ID by accident.
    """
    member = str(member).strip()
    if member.isdigit():
        return int(member)

    result = api.list_members(member, 1)
    matches = result.get("data", {}).get("data", [])
    if not matches:
        raise LibraryAPIError(f"No member found matching {member!r}.")
    if len(matches) > 1:
        options = ", ".join(f"{m.get('name')} (ID {m.get('id')})" for m in matches)
        raise LibraryAPIError(f"Multiple members match {member!r}: {options}. Ask the user which one they mean.")
    return matches[0]["id"]


def _resolve_book_id(book: str) -> int:
    """
    Resolve a numeric ID or a title/keyword into a book ID.

    Raises LibraryAPIError when there's no match or more than one —
    see _resolve_member_id above.
    """
    book = str(book).strip()
    if book.isdigit():
        return int(book)

    result = api.search_books(book)
    matches = result.get("data", [])
    if not matches:
        raise LibraryAPIError(f"No book found matching {book!r}.")
    if len(matches) > 1:
        options = ", ".join(f"{b.get('title')} (ID {b.get('id')})" for b in matches)
        raise LibraryAPIError(f"Multiple books match {book!r}: {options}. Ask the user which one they mean.")
    return matches[0]["id"]


@tool
def book_borrow_history(book: str) -> dict[str, Any]:
    """
    Show every borrow/return record for one book, across all
    members — admin accounts only. Use this to answer questions
    like "who has borrowed this book" or "how many times has this
    book been borrowed", not my_borrow_history or member_borrow_history
    (those are per-member, not per-book).

    `book` may be a numeric book ID or a title/keyword to search for
    — pass along whatever the user gave you as-is; this tool resolves
    it internally, so do not call search_books yourself first.

    If the authenticated user is not an admin, the API rejects this
    and the tool returns an error explaining that — do not retry it
    or ask the user for admin credentials, just relay the error.
    """
    try:
        book_id = _resolve_book_id(book)
        result = api.book_history(book_id)
        return {
            "success": True,
            "book": result.get("book"),
            "history": [
                {
                    "borrowed_by": (h.get("member") or {}).get("name"),
                    "borrowed_at": h.get("borrowed_at"),
                    "returned_at": h.get("returned_at"),
                }
                for h in result.get("history", [])
            ],
        }
    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def member_borrow_history(member: str) -> dict[str, Any]:
    """
    Show every borrow/return record for one member — admin accounts
    only. Use this to look up ANOTHER member's borrowing history. For
    the currently authenticated user's OWN history, use
    my_borrow_history instead (it takes no argument and works for any
    member, admin or not).

    `member` may be a numeric member ID or a name/email to search for
    — pass along whatever the user gave you as-is; this tool resolves
    it internally, so do not call list_members yourself first.

    If the authenticated user is not an admin, the API rejects this
    and the tool returns an error explaining that — do not retry it
    or ask the user for admin credentials, just relay the error.
    """
    try:
        member_id = _resolve_member_id(member)
        result = api.member_history(member_id)
        return {
            "success": True,
            "member": result.get("member"),
            "history": [
                {
                    "book_title": (h.get("book") or {}).get("title"),
                    "borrowed_at": h.get("borrowed_at"),
                    "returned_at": h.get("returned_at"),
                }
                for h in result.get("history", [])
            ],
        }
    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================
# LIBRARY STATISTICS
# ============================================================

@tool
def library_stats() -> dict[str, Any]:
    """
    Get statistics about the library: total books, available
    books, borrowed books, total borrow history, and total_members
    (the count of every member registered in the library — not
    just the currently authenticated user).
    """
    try:
        return api.library_stats()

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# ============================================================
# ALL TOOLS
# ============================================================

library_tools = [
    search_books,
    list_available_books,
    list_borrowed_books,
    list_all_books,
    get_book_details,
    my_profile,
    my_borrowed_books,
    my_borrow_history,
    borrow_book,
    return_book,
    library_stats,
    list_members,
    book_borrow_history,
    member_borrow_history,
]
