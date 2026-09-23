from langchain.tools import tool
from api_client import LibraryAPIClient, LibraryAPIError

from .redis_cache import (
    get_cache,
    set_cache,
    clear_library_cache,
)

# ---------------------------------------------------------
# Shared API client
# ---------------------------------------------------------

api: LibraryAPIClient | None = None


def set_api_client(client: LibraryAPIClient):
    global api
    api = client


def get_api_client() -> LibraryAPIClient:
    if api is None:
        raise RuntimeError("API client has not been initialized.")
    return api


# ---------------------------------------------------------
# Cache keys
# ---------------------------------------------------------

ALL_BOOKS_KEY = "library:books:all"
AVAILABLE_BOOKS_KEY = "library:books:available"
BORROWED_BOOKS_KEY = "library:books:borrowed"
STATS_KEY = "library:stats"


def search_cache_key(search: str) -> str:
    """Create a consistent Redis key for a book search."""
    normalized = search.strip().lower()
    return f"library:books:search:{normalized}"


# ---------------------------------------------------------
# Search books
# ---------------------------------------------------------

@tool
def search_books(search: str) -> str:
    """
    Search for books by title, author, or category.

    Uses Redis cache when available.
    """
    key = search_cache_key(search)

    # 1. Try Redis first
    cached = get_cache(key)
    if cached is not None:
        return str(cached)

    # 2. Cache miss -> Laravel API
    result = get_api_client().search_books(search)

    # 3. Save API result in Redis
    set_cache(key, result)

    return str(result)


# ---------------------------------------------------------
# Available books
# ---------------------------------------------------------

@tool
def list_available_books() -> str:
    """
    List all currently available books.

    Uses Redis cache when available.
    """
    cached = get_cache(AVAILABLE_BOOKS_KEY)
    if cached is not None:
        return str(cached)

    result = get_api_client().available_books()
    set_cache(AVAILABLE_BOOKS_KEY, result)

    return str(result)


# ---------------------------------------------------------
# Borrowed books
# ---------------------------------------------------------

@tool
def list_borrowed_books() -> str:
    """
    List currently borrowed books.

    Uses Redis cache when available.
    """
    cached = get_cache(BORROWED_BOOKS_KEY)
    if cached is not None:
        return str(cached)

    result = get_api_client().borrowed_books()
    set_cache(BORROWED_BOOKS_KEY, result)

    return str(result)


# ---------------------------------------------------------
# All books
# ---------------------------------------------------------

@tool
def list_all_books() -> str:
    """
    List all books in the library.

    Uses Redis cache when available.
    """
    cached = get_cache(ALL_BOOKS_KEY)
    if cached is None:
        result = get_api_client().all_books()
        set_cache(ALL_BOOKS_KEY,result)
    else:
        result=cached

    books=result.get("data",[])
    if not books:
        return "There are no books in the library"

    lines=[f"The library has {len(books)} books:"]
    for book in books:
        title = book.get("title")


        lines.append(
            f"- {title}"
        )


    return "\n".join(lines)

# ---------------------------------------------------------
# Library statistics
# ---------------------------------------------------------

@tool
def library_stats() -> str:
    """
    Get library statistics.

    Uses Redis cache when available.
    """
    cached = get_cache(STATS_KEY)
    if cached is not None:
        return str(cached)

    result = get_api_client().library_stats()
    set_cache(STATS_KEY, result)

    return str(result)


# ---------------------------------------------------------
# Borrow / Return
# ---------------------------------------------------------

@tool
def borrow_book(book: str) -> dict:
    """
    Borrow a book.

    `book` may be a numeric book ID or a title/keyword.
    The book is borrowed by the currently authenticated member.

    After a successful borrow, all library read caches are cleared
    because book availability and statistics have changed.
    """
    try:
        book = str(book).strip()

        if book.isdigit():
            book_id = int(book)

        else:
            result = get_api_client().search_books(book)
            matches = result.get("data", [])

            if not matches:
                return {
                    "success": False,
                    "message": f"No book found matching {book!r}.",
                }

            if len(matches) > 1:
                options = ", ".join(
                    f"{b.get('title')} (ID {b.get('id')})"
                    for b in matches
                )

                return {
                    "success": False,
                    "message": (
                        f"Multiple books match {book!r}: "
                        f"{options}. Ask the user which one they mean."
                    ),
                }

            book_id = matches[0]["id"]

        result = get_api_client().borrow_book(book_id)

        # Only invalidate cache after successful mutation
        if result.get("success") is True:
            clear_library_cache()

        return result

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


@tool
def return_book(book: str) -> dict:
    """
    Return a book.

    `book` may be a numeric book ID or a title/keyword.
    The book is returned by the currently authenticated member.

    After a successful return, all library read caches are cleared
    because book availability and statistics have changed.
    """
    try:
        book = str(book).strip()

        if book.isdigit():
            book_id = int(book)

        else:
            result = get_api_client().search_books(book)
            matches = result.get("data", [])

            if not matches:
                return {
                    "success": False,
                    "message": f"No book found matching {book!r}.",
                }

            if len(matches) > 1:
                options = ", ".join(
                    f"{b.get('title')} (ID {b.get('id')})"
                    for b in matches
                )

                return {
                    "success": False,
                    "message": (
                        f"Multiple books match {book!r}: "
                        f"{options}. Ask the user which one they mean."
                    ),
                }

            book_id = matches[0]["id"]

        result = get_api_client().return_book(book_id)

        # Only invalidate cache after successful mutation
        if result.get("success") is True:
            clear_library_cache()

        return result

    except LibraryAPIError as e:
        return {
            "success": False,
            "message": str(e),
        }


# ---------------------------------------------------------
# Export tools
# ---------------------------------------------------------

library_tools = [
    search_books,
    list_available_books,
    list_borrowed_books,
    list_all_books,
    borrow_book,
    return_book,
    library_stats,
]
