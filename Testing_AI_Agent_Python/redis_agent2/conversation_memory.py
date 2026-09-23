from api_client import LibraryAPIClient
from typing import cast

class ConversationMemory:
    """
    Handles persistent conversation history through the Laravel API.

    Storage flow:
        Python → Laravel API → MySQL
    """

    def __init__(
        self,
        api_client: LibraryAPIClient,
        conversation_id: int | None = None,
    ):
        self.api = api_client
        self.conversation_id = conversation_id

    # ---------------------------------------------------------
    # Conversation management
    # ---------------------------------------------------------

    def create(self, title: str | None = None) -> int:
        """Create a new conversation and store its ID."""

        result = self.api.create_conversation(title=title)

        self.conversation_id = result["conversation"]["id"]

        return self.conversation_id

    def load(self, conversation_id: int) -> dict:
        """Load a conversation from Laravel."""

        result = self.api.get_conversation(conversation_id)

        self.conversation_id = conversation_id

        return result["conversation"]

    # ---------------------------------------------------------
    # Message history
    # ---------------------------------------------------------

    def get_messages(self) -> list[dict]:
        """Return the messages from the current conversation."""

        if self.conversation_id is None:
            return []

        conversation = self.load(self.conversation_id)

        return conversation.get("messages", [])

    # ---------------------------------------------------------
    # Save messages
    # ---------------------------------------------------------

    def save_user_message(self, content: str) -> dict:
        """Save a user message."""

        self._ensure_conversation()

        conversation_id = cast(int, self.conversation_id)

        result = self.api.add_conversation_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

        return result["message"]

    def save_assistant_message(self, content: str) -> dict:
        """Save an assistant message."""

        self._ensure_conversation()

        conversation_id = cast(int, self.conversation_id)

        result = self.api.add_conversation_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
        )

        return result["message"]

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _ensure_conversation(self) -> None:
        """Make sure a conversation exists before saving messages."""

        if self.conversation_id is None:
            self.create(title="Library Assistant Conversation")



    def get_recent_messages(self, limit: int = 10) -> list[dict]:
        """
        Return the most recent conversation messages.

        MySQL keeps the complete history, but only the latest
        messages are returned for LLM context.
        """
        messages = self.get_messages()

        return messages[-limit:]
