import os
import sys
import time
from pathlib import Path
from typing import Any, cast


# ============================================================
# Make parent project directory importable
# ============================================================

_PARENT_DIR = str(Path(__file__).resolve().parent.parent)

if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)


# ============================================================
# Session / Markdown memory
# ============================================================

try:
    from .session_memory import (
        initialize_conversation,
        save_user_message,
        save_tool_result,
        save_assistant_message,
    )

    from .memory_retrieval import (
        get_compact_memory,
    )

except ImportError:
    from session_memory import (
        initialize_conversation,
        save_user_message,
        save_tool_result,
        save_assistant_message,
    )

    from memory_retrieval import (
        get_compact_memory,
    )


# ============================================================
# Imports
# ============================================================

from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)

from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

from api_client import LibraryAPIClient


# ============================================================
# Persistent conversation memory
# ============================================================

try:
    from .conversation_memory import ConversationMemory
except ImportError:
    from conversation_memory import ConversationMemory


# ============================================================
# Import Redis tools
# ============================================================

try:
    from .tools_redis import (
        library_tools,
        set_api_client,
    )
except ImportError:
    from tools_redis import (
        library_tools,
        set_api_client,
    )


# ============================================================
# Environment
# ============================================================

load_dotenv()


# ============================================================
# Authentication
# ============================================================

api = LibraryAPIClient(interactive=True)

set_api_client(api)


# ============================================================
# Persistent conversation memory
# ============================================================

conversation_memory = ConversationMemory(api)


# ============================================================
# Authenticated user identity
# ============================================================

def get_authenticated_user_context() -> str:
    """
    Get the currently authenticated user's identity from Laravel.

    This is NOT hard-coded.
    It comes from the Sanctum-authenticated API client.
    """

    try:
        profile = api.get_current_user()

        user = profile.get(
            "member",
            profile,
        )

        name = user.get(
            "name",
            "Unknown",
        )

        email = user.get(
            "email",
            "Unknown",
        )

        is_admin = user.get(
            "is_admin",
            False,
        )

        return (
            "Authenticated user:\n"
            f"- Name: {name}\n"
            f"- Email: {email}\n"
            f"- Admin: {is_admin}"
        )

    except Exception as e:

        print(
            f"[AUTH] Could not load authenticated user: {e}"
        )

        return (
            "Authenticated user information is currently "
            "unavailable. Do not guess the user's identity."
        )


# Load authenticated user once when the application starts.
AUTHENTICATED_USER_CONTEXT = (
    get_authenticated_user_context()
)


# ============================================================
# LLM
# ============================================================

model = ChatOllama(
    model=os.getenv(
        "OLLAMA_MODEL",
        "qwen3:1.7b",
    ),
    temperature=0,
    reasoning=False,
    keep_alive="30m",
    num_predict=150,
)


# ============================================================
# LangGraph short-term memory
# ============================================================

checkpointer = InMemorySaver()


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = f"""
You are a concise library assistant.

AUTHENTICATED USER:
{AUTHENTICATED_USER_CONTEXT}

- For "my profile", you MUST call my_profile.
- For "what have I borrowed?" or "my borrowed books", you MUST call my_borrowed_books.
- For "my borrowing history", you MUST call my_borrow_history.
- Never write a tool call as JSON text.
- Actually invoke the tool.
- "list members" → call list_members.
- "library statistics" → call library_stats.
- "X borrowing history" where X is a book title → call book_borrow_history.
- "X borrowing history" where X is a member name → call member_borrow_history.
- Never write a tool call as JSON text.
- Actually invoke the tool.


IDENTITY:
- The authenticated user is the person above.
- Never guess identity information.
- For name/email/admin questions, use the authenticated user information.
- For "show me my profile", call my_profile.

GENERAL:
- Use tools whenever library data is required.
- Never invent library data.
- Report tool errors directly.
- Do not claim a borrow/return succeeded unless the tool confirms success.
- Be concise.

BORROW / RETURN:
- Pass the user's book ID, title, or keyword directly to borrow_book or return_book.
- Do not search for the book first.
- Never guess an ID from conversation history.
- If the tool reports multiple matches, ask the user to choose.

HISTORY:
- my_borrow_history = authenticated user's history.
- member_borrow_history = another member's history; admin only.
- book_borrow_history = one book's history across members; admin only.
- For a person's history, use member_borrow_history.
- For a book's history, use book_borrow_history.

MEMBERS:
- list_members with no search means all members.
- Only provide a search argument when the user names a specific member.
- Member/history admin restrictions are enforced by the API.

LISTS:
- For a limited number of books, use list_all_books or list_available_books,
  then show only the requested number.
- Do not use search_books for generic requests such as "give me 10 books".
- Format lists compactly, one item per line.

MULTI-PART REQUESTS:
- Perform every requested operation in order.
- After a mutation such as borrow/return, fetch later requested data again.
- Never reuse stale tool results.

GREETING:
- For simple greetings or small talk, respond directly without tools.
"""


# ============================================================
# Recent context middleware
# ============================================================

class RecentContextMiddleware(AgentMiddleware):
    """
    Keep the full LangGraph checkpoint, but send only recent
    complete interactions to the LLM.

    The full conversation remains stored in LangGraph.

    This middleware only controls which messages are sent
    to the model for each model call.
    """

    def __init__(
        self,
        max_interactions: int = 2,
    ):
        self.max_interactions = max_interactions

    def wrap_model_call(
        self,
        request,
        handler,
    ):
        """
        Intercept every model call.

        `handler` is provided by LangChain/LangGraph.

        Calling handler(trimmed_request)
        continues the middleware chain and eventually
        sends the request to ChatOllama.
        """

        start = time.perf_counter()

        messages = request.messages

        if not messages:
            return handler(request)

        # ----------------------------------------------------
        # Separate conversation into complete interactions
        # ----------------------------------------------------

        interactions = []

        current_interaction = []

        for message in messages:

            current_interaction.append(message)

            if isinstance(message, AIMessage):

                has_tool_calls = bool(
                    getattr(
                        message,
                        "tool_calls",
                        None,
                    )
                )

                # AI message without tool calls means
                # the interaction is complete.
                if not has_tool_calls:

                    interactions.append(
                        current_interaction
                    )

                    current_interaction = []

        # Anything after the last complete interaction
        # belongs to the current request.
        current_messages = current_interaction

        previous_interactions = interactions

        recent_previous = previous_interactions[
            -self.max_interactions:
        ]

        # ----------------------------------------------------
        # Build messages sent to model
        # ----------------------------------------------------

        trimmed_messages = []

        for interaction in recent_previous:
            trimmed_messages.extend(
                interaction
            )

        trimmed_messages.extend(
            current_messages
        )

        # ----------------------------------------------------
        # Context debugging
        # ----------------------------------------------------

        print(
            f"[CONTEXT] Full messages: "
            f"{len(messages)} "
            f"→ Model messages: "
            f"{len(trimmed_messages)}"
        )

        print(
            "\n[CONTEXT DEBUG] Messages sent to model:"
        )

        for i, message in enumerate(
            trimmed_messages,
            start=1,
        ):

            content = getattr(
                message,
                "content",
                "",
            )

            print(
                f"  {i}. "
                f"{type(message).__name__}: "
                f"length={len(str(content))}"
            )

            print(
                f"     {str(content)[:300]}"
            )

        print()

        # ----------------------------------------------------
        # Approximate message size
        # ----------------------------------------------------

        approximate_characters = sum(
            len(
                str(
                    getattr(
                        message,
                        "content",
                        "",
                    )
                )
            )
            for message in trimmed_messages
        )

        print(
            "[CONTEXT] Approx characters: "
            f"{approximate_characters}"
        )

        # ----------------------------------------------------
        # Replace request messages
        # ----------------------------------------------------

        trimmed_request = request.override(
            messages=trimmed_messages
        )

        # ----------------------------------------------------
        # Continue middleware/model chain
        # ----------------------------------------------------

        result = handler(
            trimmed_request
        )

        # ----------------------------------------------------
        # Model timing
        # ----------------------------------------------------

        elapsed = (
            time.perf_counter()
            - start
        )

        print(
            "[MODEL] Model call completed in "
            f"{elapsed:.2f}s"
        )

        return result


# ============================================================
# Create agent
# ============================================================

agent = create_agent(
    model=model,
    tools=library_tools,
    system_prompt=SYSTEM_PROMPT,
    middleware=[
        RecentContextMiddleware(
            max_interactions=2
        )
    ],
    checkpointer=checkpointer,
)


# ============================================================
# Markdown episodic memory
# ============================================================

def record_user_message(
    conversation_id: int | str,
    message: str,
) -> None:
    """
    Record the user's message in Markdown
    episodic memory.
    """

    initialize_conversation(
        conversation_id
    )

    save_user_message(
        conversation_id,
        message,
    )


# ============================================================
# MySQL → LangChain message conversion
# ============================================================

def load_mysql_history_as_messages(
    conversation_id: int,
    limit: int = 10,
) -> list[Any]:
    """
    Load recent persistent conversation history from MySQL
    through the Laravel API and convert it into LangChain
    HumanMessage / AIMessage objects.

    MySQL stores the complete conversation.

    Only the latest `limit` messages are loaded into the
    current LangGraph thread when the thread has no history.
    """

    start = time.perf_counter()

    messages = conversation_memory.get_recent_messages(
        limit=limit
    )

    print(
        "[MEMORY] MySQL recent messages loaded: "
        f"{len(messages)}"
    )

    langchain_messages: list[Any] = []

    for message in messages:

        role = message.get(
            "role",
            "",
        )

        content = str(
            message.get(
                "content",
                "",
            )
        )

        if not content:
            continue

        if role == "user":

            langchain_messages.append(
                HumanMessage(
                    content=content
                )
            )

        elif role == "assistant":

            langchain_messages.append(
                AIMessage(
                    content=content
                )
            )

    print(
        "[MEMORY] MySQL → LangChain conversion: "
        f"{len(langchain_messages)} messages"
    )

    print(
        "[TIMING] load_mysql_history: "
        f"{time.perf_counter() - start:.2f}s"
    )

    return langchain_messages


# ============================================================
# Agent invocation
# ============================================================

def invoke_library_agent(
    user_input: str,
    thread_id: str,
    conversation_id: int | None = None,
) -> tuple[
    dict[str, Any],
    int,
    list[dict[str, Any]],
]:
    """
    Run the LangGraph agent and persist the conversation
    to Laravel/MySQL and Markdown episodic memory.

    Returns:

        result:
            Full LangGraph result.

        conversation_id:
            Laravel/MySQL persistent conversation ID.

        tool_calls:
            Tools used during THIS request only.

    thread_id:
        LangGraph short-term memory identifier.

    conversation_id:
        Laravel/MySQL persistent conversation identifier.

        If None, a new conversation is created.
    """

    overall_start = time.perf_counter()

    # ========================================================
    # Create persistent conversation if needed
    # ========================================================

    if conversation_id is None:

        start = time.perf_counter()

        conversation = api.create_conversation(
            title="Library Assistant"
        )

        conversation_id = int(
            conversation["conversation"]["id"]
        )

        print(
            "[TIMING] create_conversation: "
            f"{time.perf_counter() - start:.2f}s"
        )

    assert conversation_id is not None

    # Make sure ConversationMemory points to
    # the current persistent conversation.
    conversation_memory.conversation_id = (
        conversation_id
    )

    # ========================================================
    # Get current LangGraph state BEFORE this request
    # ========================================================

    previous_message_count = 0

    try:

        previous_state = checkpointer.get(
            {
                "configurable": {
                    "thread_id": thread_id,
                }
            }
        )

        if previous_state:

            previous_messages = (
                previous_state
                .get(
                    "channel_values",
                    {},
                )
                .get(
                    "messages",
                    [],
                )
            )

            previous_message_count = len(
                previous_messages
            )

    except Exception as e:

        print(
            "[MEMORY] Could not read LangGraph "
            f"checkpoint: {e}"
        )

        previous_message_count = 0

    print(
        "[MEMORY] Existing LangGraph messages: "
        f"{previous_message_count}"
    )

    # ========================================================
    # Load persistent MySQL history
    # ========================================================

    mysql_history: list[Any] = []

    # IMPORTANT:
    #
    # Only load MySQL history when this LangGraph thread
    # does not already contain conversation history.
    #
    # This prevents duplicate messages.
    if previous_message_count == 0:

        mysql_history = (
            load_mysql_history_as_messages(
                conversation_id=conversation_id,
                limit=10,
            )
        )

        if mysql_history:

            print(
                "[MEMORY] Restoring conversation from MySQL:"
            )

            for i, message in enumerate(
                mysql_history,
                start=1,
            ):

                print(
                    f"  {i}. "
                    f"{type(message).__name__}: "
                    f"{str(message.content)[:200]}"
                )

        else:

            print(
                "[MEMORY] No MySQL history to restore."
            )

    else:

        print(
            "[MEMORY] LangGraph history already exists. "
            "Skipping MySQL history injection."
        )

    # ========================================================
    # Save current user message to MySQL
    # ========================================================

    start = time.perf_counter()

    conversation_memory.save_user_message(
        user_input
    )

    print(
        "[TIMING] save_user_message: "
        f"{time.perf_counter() - start:.2f}s"
    )

    # ========================================================
    # Read compact Markdown memory
    # ========================================================

    start = time.perf_counter()

    recent_memory = get_compact_memory(
        conversation_id,
        max_interactions=3,
    )

    if recent_memory:

        print(
            "[MEMORY] Recent Markdown memory found:"
        )

        print(
            recent_memory
        )

    else:

        print(
            "[MEMORY] No previous Markdown memory found."
        )

    print(
        "[TIMING] memory.get_compact_memory: "
        f"{time.perf_counter() - start:.2f}s"
    )

    # ========================================================
    # Save current user message to Markdown
    # ========================================================

    start = time.perf_counter()

    record_user_message(
        conversation_id,
        user_input,
    )

    print(
        "[TIMING] memory.save_user_message: "
        f"{time.perf_counter() - start:.2f}s"
    )

    # ========================================================
    # Build current request
    # ========================================================

    # IMPORTANT:
    #
    # We no longer put MySQL conversation history inside the
    # current user's text.
    #
    # MySQL history is passed as real LangChain messages.

    current_user_message = HumanMessage(
        content=user_input
    )

    # ========================================================
    # Build messages for LangGraph
    # ========================================================

    messages_for_agent: list[Any]

    if (
        previous_message_count == 0
        and mysql_history
    ):

        messages_for_agent = (
            mysql_history
            + [
                current_user_message
            ]
        )

        print(
            "[MEMORY] Agent input includes "
            "persistent MySQL history."
        )

    else:

        messages_for_agent = [
            current_user_message
        ]

        print(
            "[MEMORY] Agent input uses current "
            "request + existing LangGraph state."
        )

    # ========================================================
    # Run LangGraph agent
    # ========================================================

    start = time.perf_counter()

    result = cast(
        dict[str, Any],
        agent.invoke(
            {
                "messages": messages_for_agent,
            },
            {
                "configurable": {
                    "thread_id": thread_id,
                }
            },
        ),
    )

    print(
        "[TIMING] agent.invoke: "
        f"{time.perf_counter() - start:.2f}s"
    )

    # ========================================================
    # Debug LangGraph result
    # ========================================================

    print(
        "\n========== AGENT RESULT DEBUG =========="
    )

    print(
        result
    )

    messages = (
        result.get(
            "messages",
            [],
        )
        if isinstance(result, dict)
        else []
    )

    for i, message in enumerate(
        messages,
        1,
    ):

        print(
            f"\n--- Message {i} ---"
        )

        print(
            "Type:",
            type(message).__name__,
        )

        print(
            "Content:",
            repr(
                getattr(
                    message,
                    "content",
                    None,
                )
            ),
        )

        print(
            "Tool calls:",
            getattr(
                message,
                "tool_calls",
                None,
            ),
        )

    print(
        "========================================\n"
    )

    # ========================================================
    # Debug total thread messages
    # ========================================================

    print(
        "[DEBUG] Total messages in thread: "
        f"{len(result['messages'])}"
    )

    for i, message in enumerate(
        result["messages"]
    ):

        message_type = (
            type(message).__name__
        )

        tool_names = []

        if (
            hasattr(
                message,
                "tool_calls",
            )
            and message.tool_calls
        ):

            tool_names = [
                call.get(
                    "name",
                    "unknown",
                )
                for call in message.tool_calls
            ]

        print(
            f"[DEBUG] Message {i + 1}: "
            f"{message_type}"
            + (
                f" | tools={tool_names}"
                if tool_names
                else ""
            )
        )

    # ========================================================
    # Get messages generated by THIS request
    # ========================================================

    new_messages = result["messages"][
        previous_message_count:
    ]

    # ========================================================
    # Extract THIS request's tool calls
    # ========================================================

    tool_calls: list[dict[str, Any]] = []

    for message in new_messages:

        if (
            hasattr(
                message,
                "tool_calls",
            )
            and message.tool_calls
        ):

            for tool_call in message.tool_calls:

                tool_calls.append(
                    {
                        "name": tool_call.get(
                            "name",
                            "unknown",
                        ),
                        "args": tool_call.get(
                            "args",
                            {},
                        ),
                    }
                )

    # ========================================================
    # Save tool results to Markdown episodic memory
    # ========================================================

    for message in new_messages:

        message_type = (
            type(message).__name__
        )

        if message_type == "ToolMessage":

            tool_name = getattr(
                message,
                "name",
                "unknown",
            )

            tool_result = getattr(
                message,
                "content",
                "",
            )

            save_tool_result(
                conversation_id,
                tool_name,
                str(tool_result),
            )

    # ========================================================
    # Get final assistant response
    # ========================================================

    assistant_message = str(
        result["messages"][-1].content
    )

    # ========================================================
    # Save assistant response to Markdown
    # ========================================================

    start = time.perf_counter()

    save_assistant_message(
        conversation_id,
        assistant_message,
    )

    print(
        "[TIMING] memory.save_assistant_message: "
        f"{time.perf_counter() - start:.2f}s"
    )

    # ========================================================
    # Save assistant response to MySQL
    # ========================================================

    start = time.perf_counter()

    conversation_memory.save_assistant_message(
        assistant_message
    )

    print(
        "[TIMING] save_assistant_message: "
        f"{time.perf_counter() - start:.2f}s"
    )

    # ========================================================
    # Total timing
    # ========================================================

    print(
        "[TIMING] TOTAL: "
        f"{time.perf_counter() - overall_start:.2f}s"
    )

    # ========================================================
    # Return
    # ========================================================

    return (
        result,
        conversation_id,
        tool_calls,
    )
