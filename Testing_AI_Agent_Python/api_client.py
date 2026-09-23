import getpass
import os
from typing import Any

import requests
from dotenv import find_dotenv, load_dotenv, set_key


load_dotenv()


class LibraryAPIError(Exception):
    """Raised when the Laravel Library API returns an error."""

    pass


class LibraryAPIClient:
    """
    HTTP client used by the Python AI agent to communicate
    with the Laravel Library API.
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: int = 10,
        interactive: bool = False,
    ):
        self.base_url = (
            base_url
            or os.getenv(
                "LIBRARY_API_URL",
                "http://127.0.0.1:8000/api",
            )
        ).rstrip("/")

        # Do not automatically reuse LIBRARY_API_TOKEN from .env.
        # Each process starts unauthenticated unless a token is
        # explicitly provided or login() is called.
        self.token = token

        self.timeout = timeout

        # If True, the client is allowed to ask for credentials
        # through the terminal.
        self.interactive = interactive

        self.session = requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        if self.token:
            self._set_token(self.token)

        elif self.interactive:
            self.authenticate_interactively()

    # =========================================================
    # Authentication state
    # =========================================================

    @property
    def is_authenticated(self) -> bool:
        """Return True when the client currently has an API token."""

        return bool(self.token)

    def _set_token(self, token: str) -> None:
        """
        Store the Sanctum token and attach it to future requests.
        """

        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def login(
        self,
        email: str,
        password: str,
    ) -> str:
        """
        Log in against the Laravel API.

        Returns:
            str: Sanctum authentication token.
        """

        response = self.session.post(
            f"{self.base_url}/login",
            json={
                "email": email,
                "password": password,
            },
            timeout=self.timeout,
        )

        try:
            data = response.json()

        except ValueError as e:
            raise LibraryAPIError(
                f"Login returned invalid JSON "
                f"(HTTP {response.status_code})."
            ) from e

        if not response.ok or not data.get("success", True):
            raise LibraryAPIError(
                data.get(
                    "message",
                    f"Login failed (HTTP {response.status_code}).",
                )
            )

        token: str = data["token"]

        self._set_token(token)

        # The token is intentionally NOT persisted to .env.
        return token

    def authenticate_interactively(self) -> None:
        """
        Prompt for email/password and authenticate through the
        Laravel API.

        This is intended for CLI/testing usage.
        """

        print("No valid API token found — please log in.")

        while True:
            email = input("Email: ").strip()
            password = getpass.getpass("Password: ")

            try:
                self.login(email, password)
                break

            except LibraryAPIError as e:
                print(f"Login failed: {e}\n")

        print("Logged in.\n")

    def logout(self) -> None:
        """
        Revoke the current token server-side and clear it locally.
        """

        if self.token:
            try:
                self.session.post(
                    f"{self.base_url}/logout",
                    timeout=self.timeout,
                )

            except requests.RequestException:
                # Best effort. The local token is still cleared.
                pass

        self.token = None

        self.session.headers.pop(
            "Authorization",
            None,
        )

        os.environ.pop(
            "LIBRARY_API_TOKEN",
            None,
        )

        # Clear any old persisted token if one exists.
        env_path = find_dotenv(usecwd=True) or find_dotenv()

        if env_path:
            set_key(
                env_path,
                "LIBRARY_API_TOKEN",
                "",
            )

    # =========================================================
    # AI Conversations / Persistent Memory
    # =========================================================

    def create_conversation(
        self,
        title: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new AI conversation for the authenticated member.

        Laravel automatically associates the conversation with the
        currently authenticated member.
        """

        return self.post(
            "/ai/conversations",
            json={
                "title": title,
            },
        )

    def get_conversations(self) -> dict[str, Any]:
        """
        Get all AI conversations belonging to the authenticated member.
        """

        return self.get(
            "/ai/conversations",
        )

    def get_conversation(
        self,
        conversation_id: int,
    ) -> dict[str, Any]:
        """
        Get one conversation and all of its messages.
        """

        return self.get(
            f"/ai/conversations/{conversation_id}",
        )

    def delete_conversation(
        self,
        conversation_id: int,
    ) -> dict[str, Any]:
        """
        Delete one conversation belonging to the authenticated member.
        """

        return self.delete(
            f"/ai/conversations/{conversation_id}",
        )

    def add_conversation_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> dict[str, Any]:
        """
        Add a message to an existing conversation.

        role must be:
            - user
            - assistant
        """

        return self.post(
            f"/ai/conversations/{conversation_id}/messages",
            json={
                "role": role,
                "content": content,
            },
        )

    # =========================================================
    # Internal HTTP request methods
    # =========================================================

    def _request(
        self,
        method: str,
        endpoint: str,
        _retrying: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute an HTTP request against the Laravel API.

        Handles:
            - connection errors
            - expired Sanctum tokens
            - invalid JSON
            - Laravel API errors
        """

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs,
            )

        except requests.RequestException as e:
            raise LibraryAPIError(
                f"Could not connect to Library API: {e}"
            ) from e

        # -----------------------------------------------------
        # Handle expired/revoked token
        # -----------------------------------------------------

        if response.status_code == 401 and not _retrying:

            if self.interactive:
                # CLI usage can safely ask the user to log in again.
                self.authenticate_interactively()

                return self._request(
                    method,
                    endpoint,
                    _retrying=True,
                    **kwargs,
                )

            # Web/Streamlit usage must never block waiting for input.
            self.token = None

            self.session.headers.pop(
                "Authorization",
                None,
            )

            raise LibraryAPIError(
                "Session expired. Please log in again."
            )

        # -----------------------------------------------------
        # Parse JSON
        # -----------------------------------------------------

        try:
            data = response.json()

        except ValueError as e:
            raise LibraryAPIError(
                "Library API returned invalid JSON "
                f"(HTTP {response.status_code})."
            ) from e

        # -----------------------------------------------------
        # Handle Laravel errors
        # -----------------------------------------------------

        if not response.ok:

            message = data.get(
                "message",
                f"Library API error ({response.status_code})",
            )

            raise LibraryAPIError(
                f"{message} "
                f"(HTTP {response.status_code})"
            )

        return data

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a GET request."""

        return self._request(
            "GET",
            endpoint,
            params=params,
        )

    def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a POST request."""

        return self._request(
            "POST",
            endpoint,
            json=json,
        )

    def patch(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a PATCH request."""

        return self._request(
            "PATCH",
            endpoint,
            json=json,
        )

    def delete(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """Send a DELETE request."""

        return self._request(
            "DELETE",
            endpoint,
        )

    # =========================================================
    # Authentication / Current User
    # =========================================================

    def get_current_user(self) -> dict[str, Any]:
        """Get the currently authenticated member."""

        return self.get(
            "/ai/me",
        )

    # =========================================================
    # Books
    # =========================================================

    def search_books(
        self,
        search: str,
    ) -> dict[str, Any]:
        """Search books by title/author/category/etc."""

        return self.get(
            "/ai/books/search",
            params={
                "search": search,
            },
        )

    def available_books(self) -> dict[str, Any]:
        """Get all currently available books."""

        return self.get(
            "/ai/books/available",
        )

    def borrowed_books(self) -> dict[str, Any]:
        """
        Get all currently borrowed books, including who borrowed them.

        Filtering is performed server-side.
        """

        return self.get(
            "/ai/books/borrowed",
        )

    def all_books(self) -> dict[str, Any]:
        """Get all books."""

        return self.get(
            "/ai/books",
        )

    def get_book(
        self,
        book_id: int,
    ) -> dict[str, Any]:
        """Get details for one book."""

        return self.get(
            f"/ai/books/{book_id}",
        )

    # =========================================================
    # Member
    # =========================================================

    def my_borrowed_books(self) -> dict[str, Any]:
        """Get books currently borrowed by the authenticated member."""

        return self.get(
            "/ai/member/books",
        )

    def my_borrow_history(self) -> dict[str, Any]:
        """Get the authenticated member's borrowing history."""

        return self.get(
            "/ai/member/history",
        )

    # =========================================================
    # Borrow / Return
    # =========================================================

    def borrow_book(
        self,
        book_id: int,
    ) -> dict[str, Any]:
        """Borrow a book for the authenticated member."""

        return self.post(
            f"/ai/books/{book_id}/borrow",
        )

    def return_book(
        self,
        book_id: int,
    ) -> dict[str, Any]:
        """Return a book for the authenticated member."""

        return self.post(
            f"/ai/books/{book_id}/return",
        )

    # =========================================================
    # Statistics
    # =========================================================

    def library_stats(self) -> dict[str, Any]:
        """Get library statistics."""

        return self.get(
            "/ai/stats",
        )

    # =========================================================
    # Members
    # =========================================================

    def list_members(
        self,
        search: str | None = None,
        page: int = 1,
    ) -> dict[str, Any]:
        """
        List members.

        Admin authorization is enforced by Laravel.
        """

        return self.get(
            "/members",
            params={
                "search": search,
                "page": page,
            },
        )

    # =========================================================
    # Borrow History
    # =========================================================

    def book_history(
        self,
        book_id: int,
    ) -> dict[str, Any]:
        """
        Get every borrow/return record for one book
        across all members.
        """

        return self.get(
            f"/books/{book_id}/history",
        )

    def member_history(
        self,
        member_id: int,
    ) -> dict[str, Any]:
        """
        Get every borrow/return record for one member.

        This is different from my_borrow_history(), which only
        returns the authenticated member's own history.
        """

        return self.get(
            f"/members/{member_id}/history",
        )


# =============================================================
# Direct testing
# =============================================================

if __name__ == "__main__":

    api = LibraryAPIClient(
        interactive=True,
    )

    print("Testing Laravel Library API...")

    user = api.get_current_user()

    print("\nCurrent user:")
    print(user)

    books = api.available_books()

    print("\nAvailable books:")
    print(books)
