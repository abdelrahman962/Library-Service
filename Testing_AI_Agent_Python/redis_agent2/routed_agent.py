import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

MEMORY_WINDOW=10
# =========================================================
# Project root
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# Project imports
# =========================================================

from api_client import LibraryAPIClient


try:
    from .conversation_memory import ConversationMemory
except ImportError:
    from conversation_memory import ConversationMemory


try:
    from .router import (
        get_direct_tool,
        resolve_history_tool,
        DIRECT_TOOL_GROUP,
    )
except ImportError:
    from router import (
        get_direct_tool,
        resolve_history_tool,
        DIRECT_TOOL_GROUP,
    )


try:
    from .ai_router import classify_route
except ImportError:
    from ai_router import classify_route


try:
    from .redis_cache import get_cache, set_cache
except ImportError:
    from redis_cache import get_cache, set_cache


try:
    from .tools_redis import (
        set_api_client,
        get_api_client,
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
    )
except ImportError:
    from tools_redis import (
        set_api_client,
        get_api_client,
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
    )


# =========================================================
# Shared API client
# =========================================================

api = LibraryAPIClient(
    interactive=True
)

set_api_client(api)


# =========================================================
# Tool groups
# =========================================================

BOOK_TOOLS = [
    search_books,
    list_available_books,
    list_borrowed_books,
    list_all_books,
    get_book_details,
]


USER_TOOLS = [
    my_profile,
    my_borrowed_books,
    my_borrow_history,
]


BORROWING_TOOLS = [
    borrow_book,
    return_book,
]


ADMIN_TOOLS = [
    library_stats,
    list_members,
    book_borrow_history,
    member_borrow_history,
]


# =========================================================
# Direct deterministic tools
# =========================================================

DIRECT_TOOLS = {
    "my_profile": my_profile,
    "my_borrowed_books": my_borrowed_books,
    "my_borrow_history": my_borrow_history,

    "list_members": list_members,
    "library_stats": library_stats,

    "list_all_books": list_all_books,
    "list_available_books": list_available_books,
    "list_borrowed_books": list_borrowed_books,

    "book_borrow_history": book_borrow_history,
    "member_borrow_history": member_borrow_history,
}


# =========================================================
# LLM response cache
# =========================================================
#
# Caches the final text answer for groups whose output is mostly
# data-driven (books/admin/user), scoped per authenticated user so
# answers never cross accounts. Never used for "borrowing" (a
# mutation - caching its result would be actively wrong) or
# "general" (free-form chat, leans on conversation context the most).
#
# Keys are prefixed "library:" on purpose: borrow_book/return_book's
# existing clear_library_cache() sweeps every "library:*" key, so a
# borrow/return automatically invalidates cached answers too, with
# no changes needed to redis_cache.py.

RESPONSE_CACHEABLE_GROUPS = {
    "books",
    "user",
    "admin",
}

RESPONSE_CACHE_TTL = 300  # 5 minutes


def _response_cache_key(
    group: str,
    user_message: str,
) -> str:

    token = getattr(
        get_api_client(),
        "token",
        "anonymous",
    )

    normalized = user_message.strip().lower()

    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:16]

    return f"library:ai_response:{group}:{token}:{digest}"


# =========================================================
# Model
# =========================================================

model = ChatOllama(
    model=os.getenv(
        "OLLAMA_MODEL",
        "qwen3:1.7b",
    ),
    temperature=0,
    # qwen3's chat template only emits well-formed <tool_call> tags
    # when its thinking step runs. With reasoning=False it silently
    # falls back to printing the tool call as plain JSON text, which
    # Ollama can't parse into a structured tool call - the agent
    # then treats that raw JSON as the final answer and never
    # actually calls the tool. reasoning=True keeps native tool
    # calling working.
    reasoning=True,
    keep_alive="30m",
    num_predict=150,
)


# =========================================================
# System prompts
# =========================================================
#
# Loaded once at import time from prompts/*.md - not re-read per
# request. Each group's prompt is the shared base rules plus that
# group's own instructions.

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


BASE_PROMPT = _load_prompt("base_agent.md")


GROUP_PROMPTS = {
    group: BASE_PROMPT + "\n\n" + _load_prompt(f"{group}_agent.md")
    for group in (
        "books",
        "user",
        "borrowing",
        "admin",
        "general",
    )
}


# =========================================================
# Create one agent per tool group
# =========================================================

agents = {

    "books": create_agent(
        model=model,
        tools=BOOK_TOOLS,
        system_prompt=GROUP_PROMPTS["books"],
    ),

    "user": create_agent(
        model=model,
        tools=USER_TOOLS,
        system_prompt=GROUP_PROMPTS["user"],
    ),

    "borrowing": create_agent(
        model=model,
        tools=BORROWING_TOOLS,
        system_prompt=GROUP_PROMPTS["borrowing"],
    ),

    "admin": create_agent(
        model=model,
        tools=ADMIN_TOOLS,
        system_prompt=GROUP_PROMPTS["admin"],
    ),

    "general": create_agent(
        model=model,
        tools=[],
        system_prompt=GROUP_PROMPTS["general"],
    ),
}


# =========================================================
# Memory helpers
# =========================================================

def _load_conversation_messages(
    conversation_id: int | None,
) -> list[dict[str, Any]]:
    """
    Load recent persistent conversation messages from Laravel/MySQL.

    The complete history remains in MySQL.
    Only the recent messages are sent to the LLM.
    """

    if conversation_id is None:
        return []

    memory = ConversationMemory(
        api_client=api,
        conversation_id=conversation_id,
    )

    messages = memory.get_recent_messages(
        limit=MEMORY_WINDOW
    )

    print(
        f"[MEMORY] Loaded {len(messages)} "
        f"persistent messages."
    )

    return messages


def _save_user_message(
    conversation_id: int | None,
    content: str,
) -> None:
    """
    Save the user's message to persistent MySQL memory.
    """

    if conversation_id is None:
        return

    memory = ConversationMemory(
        api_client=api,
        conversation_id=conversation_id,
    )

    memory.save_user_message(
        content
    )

    print(
        "[MEMORY] User message saved."
    )


def _save_assistant_message(
    conversation_id: int | None,
    content: str,
) -> None:
    """
    Save the assistant's final response to persistent MySQL memory.
    """

    if conversation_id is None:
        return

    memory = ConversationMemory(
        api_client=api,
        conversation_id=conversation_id,
    )

    memory.save_assistant_message(
        content
    )

    print(
        "[MEMORY] Assistant message saved."
    )


def _convert_history_to_langchain_messages(
    history: list[dict[str, Any]],
) -> list[Any]:
    """
    Convert Laravel conversation messages into the format
    accepted by LangChain create_agent().

    Any is intentional here because LangChain accepts multiple
    message representations, including dictionaries and
    BaseMessage objects.
    """

    messages: list[Any] = []

    for message in history:

        role = message.get("role")
        content = message.get("content")

        if not role or content is None:
            continue

        messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    return messages


def _extract_final_assistant_response(
    result: Any,
) -> str:
    """
    Extract the final assistant text from a LangChain agent result.
    """

    messages = result.get(
        "messages",
        [],
    )

    # Search backwards because the final AI message is
    # normally at the end of the agent result.
    for message in reversed(messages):

        content = getattr(
            message,
            "content",
            None,
        )

        if content is None:
            continue

        if isinstance(content, str):

            if content.strip():
                return content.strip()

        else:

            try:
                return json.dumps(
                    content,
                    ensure_ascii=False,
                )
            except TypeError:
                return str(content)

    return "No response returned."


def _serialize_direct_response(
    result: Any,
) -> str:
    """
    Convert a deterministic tool result into text suitable
    for persistent conversation memory.

    The original result is still returned unchanged to Streamlit.
    """

    if isinstance(result, str):
        return result

    try:
        return json.dumps(
            result,
            ensure_ascii=False,
        )
    except TypeError:
        return str(result)


# =========================================================
# Routed invocation
# =========================================================

def invoke_routed_agent(
    user_message: str,
    conversation_id: int | None = None,
):
    """
    Route the request to the appropriate specialized agent.

    Persistent conversation memory:

        Python
            ↓
        Laravel API
            ↓
        MySQL

    The complete conversation remains in MySQL.
    Recent messages are restored before invoking the selected
    specialized LLM agent.

    Simple, unambiguous requests are executed directly
    (router.get_direct_tool) with no LLM involved at all.

    Borrowing-history requests are resolved deterministically
    to either:
        - member_borrow_history
        - book_borrow_history

    Everything else is classified by the AI router
    (ai_router.classify_route) into books/user/borrowing/admin,
    then sent to that group's specialized LLM agent.

    The existing return shape is preserved:

        return result, group
    """

    # =====================================================
    # Step 0: Load persistent conversation history
    # =====================================================

    persistent_history = _load_conversation_messages(
        conversation_id
    )

    langchain_history = (
        _convert_history_to_langchain_messages(
            persistent_history
        )
    )

    # =====================================================
    # Step 1: Check for a simple deterministic tool
    # =====================================================

    direct_tool_name = get_direct_tool(
        user_message
    )

    # =====================================================
    # Step 2: Resolve borrowing-history requests
    # =====================================================
    #
    # Also deterministic - checked before the AI router so an
    # exact/resolvable request never pays for an LLM call.

    history_resolution = None

    if direct_tool_name is None:

        try:

            history_resolution = resolve_history_tool(
                user_message,
                get_api_client(),
            )

            if history_resolution is not None:

                direct_tool_name = (
                    history_resolution[0]
                )

        except ValueError as e:

            print(
                f"[ROUTER] History resolution error: "
                f"{e}"
            )

            return {
                "messages": [],
                "direct": True,
                "tool": None,
                "error": str(e),
            }, "admin"  # history requests are always admin-category

    # =====================================================
    # Step 3: Determine the tool group
    # =====================================================
    #
    # Direct hits get a free, static label (no LLM call). Only
    # requests that didn't resolve to a deterministic tool are
    # sent to the AI router.

    if direct_tool_name is not None:

        group = DIRECT_TOOL_GROUP.get(
            direct_tool_name,
            "general",
        )

    else:

        group = classify_route(
            user_message
        )

    # =====================================================
    # Router debug information
    # =====================================================

    print()
    print("=" * 60)

    print(
        f"[ROUTER] Request           : "
        f"{user_message}"
    )

    print(
        f"[ROUTER] Group             : "
        f"{group}"
    )

    print(
        f"[ROUTER] Direct tool       : "
        f"{direct_tool_name}"
    )

    print(
        f"[ROUTER] History resolution: "
        f"{history_resolution}"
    )

    print(
        f"[ROUTER] Persistent memory : "
        f"{len(langchain_history)} messages"
    )

    print("=" * 60)

    # =====================================================
    # Save current user message
    # =====================================================

    _save_user_message(
        conversation_id,
        user_message,
    )

    # =====================================================
    # Direct deterministic execution
    # =====================================================

    if direct_tool_name is not None:

        tool = DIRECT_TOOLS[
            direct_tool_name
        ]

        print(
            f"[ROUTER] Executing directly: "
            f"{direct_tool_name}"
        )

        try:

            # -------------------------------------------------
            # History tools require an argument.
            # -------------------------------------------------

            if history_resolution is not None:

                target = (
                    history_resolution[1]
                )

                if (
                    direct_tool_name
                    == "member_borrow_history"
                ):

                    result = tool.invoke(
                        {
                            "member": target
                        }
                    )

                elif (
                    direct_tool_name
                    == "book_borrow_history"
                ):

                    result = tool.invoke(
                        {
                            "book": target
                        }
                    )

                else:

                    result = tool.invoke({})

            else:

                # -------------------------------------------------
                # Normal direct tools require no arguments.
                # -------------------------------------------------

                result = tool.invoke({})

        except Exception as e:

            error_message = str(e)

            _save_assistant_message(
                conversation_id,
                error_message,
            )

            return {
                "messages": [],
                "direct": True,
                "tool": direct_tool_name,
                "error": error_message,
            }, group

        # -------------------------------------------------
        # Save deterministic tool response to memory.
        # -------------------------------------------------

        assistant_content = (
            _serialize_direct_response(
                result
            )
        )

        _save_assistant_message(
            conversation_id,
            assistant_content,
        )

        return {
            "messages": [],
            "direct": True,
            "tool": direct_tool_name,
            "response": result,
        }, group

    # =====================================================
    # LLM agent execution
    # =====================================================

    # -----------------------------------------------------
    # Response cache: skip the LLM call entirely on a hit.
    # -----------------------------------------------------

    response_cache_key = None

    if group in RESPONSE_CACHEABLE_GROUPS:

        response_cache_key = _response_cache_key(
            group,
            user_message,
        )

        cached_response = get_cache(
            response_cache_key
        )

        if cached_response is not None:

            print(
                f"[RESPONSE_CACHE] HIT for "
                f"group={group}"
            )

            _save_assistant_message(
                conversation_id,
                cached_response,
            )

            return {
                "messages": [],
                "direct": True,
                "tool": None,
                "response": cached_response,
                "cached": True,
            }, group

        print(
            f"[RESPONSE_CACHE] MISS for "
            f"group={group}"
        )

    print(
        f"[ROUTER] Sending request to "
        f"{group} LLM agent"
    )

    selected_agent = agents[
        group
    ]

    # -----------------------------------------------------
    # Build messages using persistent history.
    # -----------------------------------------------------

    messages_for_agent: list[Any] = (
        langchain_history
        + [
            {
                "role": "user",
                "content": user_message,
            }
        ]
    )

    print(
        f"[MEMORY] Sending "
        f"{len(messages_for_agent)} messages "
        f"to {group} agent."
    )

    result = selected_agent.invoke(
        {
            "messages": messages_for_agent,
        }
    )

    # =====================================================
    # Extract and persist assistant response
    # =====================================================

    assistant_response = (
        _extract_final_assistant_response(
            result
        )
    )

    _save_assistant_message(
        conversation_id,
        assistant_response,
    )

    if response_cache_key is not None:

        set_cache(
            response_cache_key,
            assistant_response,
            ttl=RESPONSE_CACHE_TTL,
        )

    return result, group
