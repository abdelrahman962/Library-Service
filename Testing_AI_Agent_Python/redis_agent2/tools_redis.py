import sys
from pathlib import Path
from typing import Any

from langchain.tools import tool


# =========================================================
# Project root
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from api_client import LibraryAPIClient, LibraryAPIError

# =========================================================
# Redis cache
# =========================================================

try:
    from .redis_cache import (
        get_cache,
        set_cache,
        clear_library_cache,
    )
except ImportError:
    from redis_cache import (
        get_cache,
        set_cache,
        clear_library_cache,
    )


# =========================================================
# Shared API client
# =========================================================

api: LibraryAPIClient | None = None


def set_api_client(client: LibraryAPIClient):
    global api
    api = client


def get_api_client() -> LibraryAPIClient:
    if api is None:
        raise RuntimeError("API client has not been initialized.")
    return api


# =========================================================
# Cache keys
# =========================================================

ALL_BOOKS_KEY = "library:books:all"
AVAILABLE_BOOKS_KEY = "library:books:available"
BORROWED_BOOKS_KEY = "library:books:borrowed"
STATS_KEY = "library:stats"


def search_cache_key(search: str) -> str:
    normalized = search.strip().lower()
    return f"library:books:search:{normalized}"


def book_details_cache_key(book_id: int) -> str:
    return f"library:books:id:{book_id}"


def members_cache_key(search: str) -> str:
    normalized = search.strip().lower()
    return f"library:members:{normalized or 'all'}"


def book_history_cache_key(book: str) -> str:
    normalized = str(book).strip().lower()
    return f"library:books:history:{normalized}"


def member_history_cache_key(member: str) -> str:
    normalized = str(member).strip().lower()
    return f"library:members:history:{normalized}"


def my_profile_cache_key(token: str | None) -> str:
    return f"library:member:profile:{token}"


def my_borrowed_books_cache_key(token: str | None) -> str:
    return f"library:member:borrowed:{token}"


def my_borrow_history_cache_key(token: str | None) -> str:
    return f"library:member:history:{token}"


# =========================================================
# Shared ID resolution
# =========================================================

def _resolve_book_id(book: str) -> int:
    """
    Resolve a numeric ID or title/keyword into a book ID.
    """

    book = str(book).strip()

    if book.isdigit():
        return int(book)

    result = get_api_client().search_books(book)
    matches = result.get("data", [])

    if not matches:
        raise LibraryAPIError(
            f"No book found matching {book!r}."
        )

    if len(matches) > 1:
        options = ", ".join(
            f"{b.get('title')} (ID {b.get('id')})"
            for b in matches
        )

        raise LibraryAPIError(
            f"Multiple books match {book!r}: {options}. "
            "Ask the user which one they mean."
        )

    return matches[0]["id"]


def _resolve_member_id(member: str) -> int:
    """
    Resolve a numeric ID or name/email into a member ID.
    """

    member = str(member).strip()

    if member.isdigit():
        return int(member)

    result = get_api_client().list_members(
        member,
        1,
    )

    matches = result.get("data", {}).get(
        "data",
        [],
    )

    if not matches:
        raise LibraryAPIError(
            f"No member found matching {member!r}."
        )

    if len(matches) > 1:
        options = ", ".join(
            f"{m.get('name')} (ID {m.get('id')})"
            for m in matches
        )

        raise LibraryAPIError(
            f"Multiple members match {member!r}: {options}. "
            "Ask the user which one they mean."
        )

    return matches[0]["id"]


# =========================================================
# Search books
# =========================================================

@tool
def search_books(search: str) -> str:
    """
    Search for books by title, author, or category.

    Return only the matching book title, author, and category.
    Do not return unnecessary API fields.
    """

    key = search_cache_key(search)

    cached = get_cache(key)

    if cached is not None:
        result = cached
    else:
        result = get_api_client().search_books(search)
        set_cache(key, result)

    books = result.get("data", [])

    if not books:
        return f"No books found matching '{search}'."

    lines = []

    for book in books:
        title = book.get("title", "Unknown")
        author = book.get("author", "Unknown")
        category = book.get("category", "Unknown")

        lines.append(
            f"- {title} — {author} — {category}"
        )

    return "\n".join(lines)


# =========================================================
# Available books
# =========================================================

@tool
def list_available_books() -> str:
    """
    List all currently available books.

    Return only the book titles.
    """

    cached = get_cache(AVAILABLE_BOOKS_KEY)

    if cached is not None:
        result = cached
    else:
        result = get_api_client().available_books()
        set_cache(
            AVAILABLE_BOOKS_KEY,
            result,
        )

    books = result.get("data", [])

    if not books:
        return "There are no available books."

    lines = [
        f"Available books ({len(books)}):"
    ]

    for book in books:
        lines.append(
            f"- {book.get('title', 'Unknown')}"
        )

    return "\n".join(lines)


# =========================================================
# Borrowed books
# =========================================================

@tool
def list_borrowed_books() -> str:
    """
    List ALL books currently borrowed by ANY member.

    Use this for library-wide requests such as:
    - "show borrowed books"
    - "list all borrowed books"
    - "what books are currently borrowed?"

    Do NOT use this for "my borrowed books".

    Return only:
    - book title
    - author
    - borrower name

    Do not return IDs, emails, categories, publish years,
    or other API fields.
    """

    cached = get_cache(BORROWED_BOOKS_KEY)

    if cached is not None:
        result = cached
    else:
        result = get_api_client().borrowed_books()
        set_cache(
            BORROWED_BOOKS_KEY,
            result,
        )

    books = result.get("data", [])

    if not books:
        return "No books are currently borrowed."

    lines = [
        f"Currently borrowed books ({len(books)}):"
    ]

    for book in books:
        title = book.get("title", "Unknown")
        author = book.get("author", "Unknown")

        borrower = book.get("borrowed_by") or {}
        borrower_name = borrower.get(
            "name",
            "Unknown",
        )

        lines.append(
            f"- {title} — {author} — borrowed by {borrower_name}"
        )

    return "\n".join(lines)


# =========================================================
# All books
# =========================================================

@tool
def list_all_books() -> str:
    """
    List all books in the library.

    Return only the book titles unless the user explicitly
    asks for additional book information.
    """

    cached = get_cache(ALL_BOOKS_KEY)

    if cached is None:
        result = get_api_client().all_books()
        set_cache(
            ALL_BOOKS_KEY,
            result,
        )
    else:
        result = cached

    books = result.get("data", [])

    if not books:
        return "There are no books in the library."

    lines = [
        f"The library has {len(books)} books:"
    ]

    for book in books:
        lines.append(
            f"- {book.get('title', 'Unknown')}"
        )

    return "\n".join(lines)


# =========================================================
# Book details
# =========================================================

@tool
def get_book_details(book: str) -> dict[str, Any]:
    """
    Get details for one specific book.

    ```
    `book` may be:
    - a numeric book ID
    - a book title
    - a title keyword

    Resolve the book to its real database ID before
    calling the API.

    Return only:
    title, author, category, publication year,
    and current borrower if applicable.
    """

    try:
        # -------------------------------------------------
        # Resolve title/keyword/ID to the real book ID
        # -------------------------------------------------
        book_id = _resolve_book_id(book)

        # -------------------------------------------------
        # Check cache using the REAL book ID
        # -------------------------------------------------
        key = book_details_cache_key(book_id)

        cached = get_cache(key)

        if cached is not None:
            result = cached
        else:
            result = get_api_client().get_book(book_id)

            set_cache(
                key,
                result,
            )

        # -------------------------------------------------
        # Extract book data
        # -------------------------------------------------
        book_data = result.get(
            "book",
            result.get("data", result),
        )

        if not book_data:
            return {
                "success": False,
                "message": "Book not found.",
            }

        # -------------------------------------------------
        # Current borrower
        # -------------------------------------------------
        borrower = book_data.get("member")

        # -------------------------------------------------
        # Return only required information
        # -------------------------------------------------
        response = {
            "success": True,
            "title": book_data.get("title"),
            "author": book_data.get("author"),
            "category": book_data.get("category"),
            "publish_year": book_data.get("publish_year"),
            "borrowed_by": (
                borrower.get("name")
                if borrower
                else None
            ),
        }

        return response

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# =========================================================
# Library statistics
# =========================================================

@tool
def library_stats() -> str:
    """
    Get library statistics.

    Return only the statistics needed to answer
    the user's question.
    """

    cached = get_cache(STATS_KEY)

    if cached is not None:
        result = cached
    else:
        result = get_api_client().library_stats()

        set_cache(
            STATS_KEY,
            result,
        )

    stats = result.get(
        "data",
        result,
    )

    if not stats:
        return "No library statistics are available."

    lines = []

    if "total_books" in stats:
        lines.append(
            f"Total books: {stats['total_books']}"
        )

    if "available_books" in stats:
        lines.append(
            f"Available books: {stats['available_books']}"
        )

    if "borrowed_books" in stats:
        lines.append(
            f"Borrowed books: {stats['borrowed_books']}"
        )

    if "total_members" in stats:
        lines.append(
            f"Total members: {stats['total_members']}"
        )

    if not lines:
        return str(stats)

    return "\n".join(lines)


# =========================================================
# My profile
# =========================================================

@tool
def my_profile() -> dict[str, Any]:
    """
    Get the authenticated user's own profile.

    Use this for:
    - name
    - email
    - admin status

    Return only name, email, and admin status.
    """

    try:
        key = my_profile_cache_key(
            get_api_client().token
        )

        cached = get_cache(key)

        if cached is not None:
            result = cached
        else:
            result = get_api_client().get_current_user()

            set_cache(
                key,
                result,
            )

        # Laravel /api/ai/me returns:
        # {
        #     "success": true,
        #     "data": {
        #         "id": ...,
        #         "name": ...,
        #         "email": ...,
        #         "is_admin": ...
        #     }
        # }

        user = result.get("data", {})

        return {
            "name": user.get("name"),
            "email": user.get("email"),
            "is_admin": user.get("is_admin"),
        }

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }

# =========================================================
# My borrowed books
# =========================================================

@tool
def my_borrowed_books() -> str:
    """
    List ONLY the books currently borrowed by
    the authenticated user.

    Use only for requests such as:
    - "show my borrowed books"
    - "what books did I borrow?"
    - "what have I borrowed?"

    Return only the book titles.
    """

    try:
        key = my_borrowed_books_cache_key(
            get_api_client().token
        )

        cached = get_cache(key)

        if cached is not None:
            result = cached
        else:
            result = get_api_client().my_borrowed_books()

            set_cache(
                key,
                result,
            )

        books = result.get(
            "data",
            [],
        )

        if not books:
            return "You have no borrowed books."

        lines = [
            f"Your borrowed books ({len(books)}):"
        ]

        for book in books:
            lines.append(
                f"- {book.get('title', 'Unknown')}"
            )

        return "\n".join(lines)

    except LibraryAPIError as e:
        return f"Error: {e}"


# =========================================================
# My borrow history
# =========================================================

@tool
def my_borrow_history() -> str:
    """
    Show the authenticated user's borrowing history.

    Return only:
    - book title
    - borrowed date
    - returned date
    """

    try:
        key = my_borrow_history_cache_key(
            get_api_client().token
        )

        cached = get_cache(key)

        if cached is not None:
            result = cached
        else:
            result = get_api_client().my_borrow_history()

            set_cache(
                key,
                result,
            )

        history = result.get(
            "history",
            result.get("data", []),
        )

        if not history:
            return "You have no borrowing history."

        lines = [
            f"Your borrowing history ({len(history)}):"
        ]

        for item in history:
            book = item.get("book") or {}

            title = item.get(
                "book_title",
                book.get(
                    "title",
                    "Unknown",
                ),
            )

            borrowed_at = item.get(
                "borrowed_at",
                "Unknown",
            )

            returned_at = item.get(
                "returned_at"
            )

            if returned_at:
                lines.append(
                    f"- {title} — borrowed {borrowed_at} — "
                    f"returned {returned_at}"
                )
            else:
                lines.append(
                    f"- {title} — borrowed {borrowed_at} — "
                    f"not returned"
                )

        return "\n".join(lines)

    except LibraryAPIError as e:
        return f"Error: {e}"


# =========================================================
# Members
# =========================================================

@tool
def list_members(search: str = "") -> str:
    """
    List library members or find a specific member.

    For all members:
        return name, email, and admin status.

    For one specific member:
        also return their borrowed books.

    Do not return password hashes or other unnecessary
    API fields.
    """

    try:
        key = members_cache_key(search)

        response = get_cache(key)

        if response is None:
            response = _fetch_members(search)

            set_cache(
                key,
                response,
            )

        return _format_members(
            response,
            search,
        )

    except LibraryAPIError as e:
        return f"Error: {e}"


def _fetch_members(
    search: str,
) -> dict[str, Any]:
    """
    Fetch all matching members and keep only fields
    useful to the assistant.
    """

    members = []

    last_page = 1
    page = 1

    while page <= last_page and page <= 20:

        result = get_api_client().list_members(
            search or None,
            page,
        )

        paginator = result.get(
            "data",
            {},
        )

        members.extend(
            paginator.get(
                "data",
                [],
            )
        )

        last_page = paginator.get(
            "last_page",
            page,
        )

        page += 1

    return {
        "success": True,
        "data": [
            {
                "id": member.get("id"),
                "name": member.get("name"),
                "email": member.get("email"),
                "is_admin": member.get("is_admin"),
                "borrowed_books": [
                    {
                        "id": book.get("id"),
                        "title": book.get("title"),
                    }
                    for book in (
                        member.get("books") or []
                    )
                ],
            }
            for member in members
        ],
        "count": len(members),
    }


def _format_members(
    response: dict[str, Any],
    search: str,
) -> str:

    members = response.get(
        "data",
        [],
    )

    if not members:
        if search:
            return (
                f"No members found matching '{search}'."
            )

        return "There are no members in the library."

    # One member: provide useful details.
    if len(members) == 1:

        member = members[0]

        lines = [
            f"Name: {member.get('name')}",
            f"Email: {member.get('email')}",
            (
                f"Admin: "
                f"{'Yes' if member.get('is_admin') else 'No'}"
            ),
        ]

        books = member.get(
            "borrowed_books",
            [],
        )

        if books:
            lines.append("Borrowed books:")

            for book in books:
                lines.append(
                    f"- {book.get('title')}"
                )
        else:
            lines.append(
                "Borrowed books: none"
            )

        return "\n".join(lines)

    # Multiple members: keep it compact.
    lines = [
        f"Members ({len(members)}):"
    ]

    for member in members:

        admin_tag = (
            " — Admin"
            if member.get("is_admin")
            else ""
        )

        lines.append(
            f"- {member.get('name')} "
            f"({member.get('email')})"
            f"{admin_tag}"
        )

    return "\n".join(lines)


# =========================================================
# Book borrow history
# =========================================================

@tool
def book_borrow_history(
    book: str,
) -> str:
    """
    Show borrowing history for one book.

    Use for questions such as:
    - "who borrowed this book?"
    - "who has borrowed this book?"
    - "how many times was this book borrowed?"

    Return only borrower name, borrowed date,
    and returned date.
    """

    try:
        key = book_history_cache_key(book)

        cached = get_cache(key)

        if cached is not None:
            response = cached
        else:
            book_id = _resolve_book_id(book)

            result = get_api_client().book_history(book_id)

            raw_book = result.get("book")

            if isinstance(raw_book, dict):
                book_info = raw_book
                title = raw_book.get("title", book)
            else:
                book_info = {}
                title = str(raw_book or book)

            raw_history = result.get("history", [])

            history = []

            for item in raw_history:
                if not isinstance(item, dict):
                    continue

                member = item.get("member") or {}

                if not isinstance(member, dict):
                    member = {}

                history.append(
                    {
                        "borrowed_by": member.get("name"),
                        "borrowed_at": item.get("borrowed_at"),
                        "returned_at": item.get("returned_at"),
                    }
                )

            response = {
                "success": True,
                "book": book_info,
                "title": title,
                "history": history,
            }

            set_cache(key, response)

        history = response.get("history", [])

        title = response.get("title", book)

        if not history:
            return (
                f"No borrowing history found for "
                f"{title}."
            )

        lines = [
            f"Borrowing history for {title}:"
        ]

        for item in history:

            borrower = item.get(
                "borrowed_by",
                "Unknown",
            )

            borrowed_at = item.get(
                "borrowed_at",
                "Unknown",
            )

            returned_at = item.get(
                "returned_at"
            )

            if returned_at:
                lines.append(
                    f"- {borrower} — borrowed "
                    f"{borrowed_at} — returned "
                    f"{returned_at}"
                )
            else:
                lines.append(
                    f"- {borrower} — borrowed "
                    f"{borrowed_at} — not returned"
                )

        return "\n".join(lines)

    except LibraryAPIError as e:
        return f"Error: {e}"

# =========================================================
# Member borrow history
# =========================================================
@tool
def member_borrow_history(member: str) -> str:
    """Get the borrowing history for a library member."""
    try:
        key = member_history_cache_key(member)

        cached = get_cache(key)

        if cached is not None:
            response = cached
        else:
            member_id = _resolve_member_id(member)
            result = get_api_client().member_history(member_id)

            raw_member = result.get("member")

            if isinstance(raw_member, dict):
                member_name = raw_member.get("name", member)
            else:
                member_name = str(raw_member or member)

            raw_history = result.get("history", [])

            history = []

            for item in raw_history:
                if not isinstance(item, dict):
                    continue

                book = item.get("book") or {}

                if not isinstance(book, dict):
                    book = {}

                history.append(
                    {
                        "book_title": book.get(
                            "title",
                            "Unknown book"
                        ),
                        "borrowed_at": item.get("borrowed_at"),
                        "returned_at": item.get("returned_at"),
                    }
                )

            response = {
                "success": True,
                "member": member_name,
                "history": history,
            }

            set_cache(key, response)

        member_name = response.get("member", member)
        history = response.get("history", [])

        if not history:
            return f"No borrowing history found for {member_name}."

        lines = [
            f"Borrowing history for {member_name}:"
        ]

        for item in history:
            book_title = item.get(
                "book_title",
                "Unknown book"
            )

            borrowed_at = item.get(
                "borrowed_at",
                "Unknown"
            )

            returned_at = item.get("returned_at")

            if returned_at:
                lines.append(
                    f"- {book_title} — "
                    f"borrowed {borrowed_at} — "
                    f"returned {returned_at}"
                )
            else:
                lines.append(
                    f"- {book_title} — "
                    f"borrowed {borrowed_at} — "
                    f"not returned"
                )

        return "\n".join(lines)

    except LibraryAPIError as e:
        return f"Error: {e}"

# =========================================================
# Borrow book
# =========================================================

@tool
def borrow_book(book: str) -> dict[str, Any]:
    """
    Borrow a book. `book` may be a numeric book ID or a title/keyword
    to search for — pass along whatever the user gave you as-is.

    The book is borrowed by the currently authenticated member.
    """
    try:
        book_id = _resolve_book_id(book)

        result = get_api_client().borrow_book(book_id)

        # -----------------------------------------------------
        # The database changed.
        # Remove all potentially stale library cache entries.
        # -----------------------------------------------------
        if result.get("success") is True:
            clear_library_cache()

        return result

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# =========================================================
# Return book
# =========================================================

@tool
def return_book(book: str) -> dict[str, Any]:
    """
    Return a book. `book` may be a numeric book ID or a title/keyword
    to search for — pass along whatever the user gave you as-is.

    The book is returned by the currently authenticated member.
    """
    try:
        book_id = _resolve_book_id(book)

        result = get_api_client().return_book(book_id)

        # -----------------------------------------------------
        # The database changed.
        # Remove all potentially stale library cache entries.
        # -----------------------------------------------------
        if result.get("success") is True:
            clear_library_cache()

        return result

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# =========================================================
# Export tools
# =========================================================

library_tools = [
    search_books,
    list_available_books,
    list_borrowed_books,
    list_all_books,
    get_book_details,
    my_profile,
    my_borrowed_books,
    borrow_book,
    return_book,
    library_stats,
    list_members,
    book_borrow_history,
    member_borrow_history,
    my_borrow_history,
]
