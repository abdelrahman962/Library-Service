"""
Streamlit chat interface for the AI Library Assistant.

Run with (from the Testing_AI_Agent_Python directory):
    streamlit run langchain_agent/streamlit_app.py
"""

import json
import os
import sys
import time

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, trim_messages

# api_client.py lives one level up (Testing_AI_Agent_Python/), shared
# across every agent folder — see agent.py's own path-fix comment.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memory
from agent import OLLAMA_MODEL, SYSTEM_PROMPT, agent
from api_client import LibraryAPIClient, LibraryAPIError
from cache import get_cached, set_cached
from tools import set_api

load_dotenv()

# How many of the most recent agent_history messages get sent to the
# model each turn. agent_history itself (and what's saved to Redis)
# is never trimmed by this — only what's actually fed into invoke()
# each turn is capped, so the prompt stops growing every single turn
# as a session goes on. Counts messages, not tokens (tool call/result
# pairs count as messages too, so this is a rough budget, not an
# exact token limit).
_MAX_HISTORY_MESSAGES = 20

# Cache key "tool name" for the final-answer response cache below —
# lives in the same Redis namespace/TTL as cache.py's tool-result
# cache, so cache.invalidate_all() (already called on every successful
# borrow/return) sweeps this up too with no extra invalidation code.
_RESPONSE_CACHE_TOOL = "agent_response"


# ============================================================
# VERIFY-AND-CORRECT
# ============================================================
# qwen3:1.7b is small enough that on a multi-part request (e.g.
# "return book X, then show my borrowed books, then show updated
# stats") it sometimes skips re-calling a tool for the last part and
# instead free-hand guesses plausible-looking numbers instead of
# reporting what the tool actually returned — see this project's
# chat history for confirmed examples (stats that don't even sum to
# themselves, a "total books" count that changed after a return,
# which is impossible).
#
# Rather than trust the model's prose for these tools, we read the
# ACTUAL ToolMessage payloads LangChain already recorded for this
# turn (that's the tool's real, un-retold JSON — see agent.invoke()
# below) and render our own block from it. That block is appended
# after the model's reply rather than edited into it, since
# rewriting numbers embedded inside free-form prose would need
# fragile guesswork about the model's exact phrasing — appending a
# clearly-labeled, always-correct block is simple and can't be wrong.

def _format_book_line(book: dict) -> str:
    if book.get("borrowed_by"):
        status = f"Borrowed by {book['borrowed_by']['name']}"
    elif book.get("available"):
        status = "Available"
    else:
        status = "Borrowed"
    return (
        f"- [{book['id']}] {book['title']} - {book['author']} "
        f"({book['category']}, {book['publish_year']}) - {status}"
    )


def _format_book_list(books: list) -> str:
    return "\n".join(_format_book_line(b) for b in books) if books else "None."


def _format_history_line(entry: dict) -> str:
    book = entry.get("book") or {}
    title = book.get("title", f"Book #{entry.get('book_id')}")
    returned_at = entry.get("returned_at")
    status = f"returned {returned_at}" if returned_at else "still borrowed"
    return f"- {title} - borrowed {entry.get('borrowed_at')} ({status})"


def _format_stats(stats: dict) -> str:
    return (
        f"- Total books: {stats['total_books']}\n"
        f"- Available: {stats['available_books']}\n"
        f"- Borrowed: {stats['borrowed_books']}\n"
        f"- Total members: {stats['total_members']}\n"
    )


# Tool name -> (verified block heading, formatter for its `data`).
_VERIFIED_TOOLS = {
    "library_stats": ("Actual current library statistics", _format_stats),
    "my_borrowed_books": ("Your actual currently borrowed books", _format_book_list),
    "my_borrow_history": ("Your actual borrow history", lambda data: "\n".join(
        _format_history_line(e) for e in data
    ) if data else "None."),
}


def build_verified_block(new_messages: list) -> str | None:
    """
    Scan the ToolMessages LangChain recorded for this turn and, for
    any of _VERIFIED_TOOLS that were actually called, render a block
    from their real JSON payload (last call wins if called more than
    once). Returns None if none of those tools were called this turn.
    """
    sections = {}
    for msg in new_messages:
        name = getattr(msg, "name", None)
        if name not in _VERIFIED_TOOLS:
            continue
        try:
            payload = json.loads(msg.content)
            data = payload["data"]
        except (ValueError, KeyError, TypeError):
            continue
        heading, formatter = _VERIFIED_TOOLS[name]
        try:
            sections[name] = f"**{heading} (from the API, not the model):**\n{formatter(data)}"
        except (KeyError, TypeError):
            continue

    if not sections:
        return None
    return "\n\n".join(sections.values())


_MUTATING_TOOLS = {"borrow_book", "return_book"}


def library_state_changed(new_messages: list) -> bool:
    """
    True if a borrow_book/return_book call actually succeeded this
    turn. Observed failure mode: after such a call, the model
    sometimes skips re-calling library_stats/my_borrowed_books for
    the rest of a chained request and free-hand guesses numbers
    instead — so build_verified_block() finds no ToolMessage for
    those tools and returns None, even though the data DID just
    change and a fresh read is exactly what's needed. This flags
    that case so the caller can fetch the real state itself instead
    of relying on the model to have asked for it.
    """
    for msg in new_messages:
        if getattr(msg, "name", None) not in _MUTATING_TOOLS:
            continue
        try:
            if json.loads(msg.content).get("success"):
                return True
        except (ValueError, AttributeError):
            continue
    return False


def fetch_verified_block() -> str | None:
    """
    Directly call library_stats/my_borrowed_books ourselves — not
    through the LLM — and build the same style block from them.
    Used as a fallback for library_state_changed() turns where the
    model didn't (re)call these itself.
    """
    try:
        stats = api.library_stats()["data"]
        borrowed = api.my_borrowed_books()["data"]
    except Exception:
        return None
    return (
        f"**Your actual currently borrowed books (from the API, not the model):**\n"
        f"{_format_book_list(borrowed)}\n\n"
        f"**Actual current library statistics (from the API, not the model):**\n"
        f"{_format_stats(stats)}"
    )


st.set_page_config(
    page_title="AI Library Assistant",
    page_icon="📚",
    layout="centered",
)


# ============================================================
# SESSION STATE
# ============================================================

if "api_client" not in st.session_state:
    # One client PER BROWSER SESSION, not a shared module-level
    # singleton — a single shared client used to mean logging in on
    # one tab silently reauthenticated every other tab's next tool
    # call as the new member (confirmed: one member was shown another
    # member's real profile). This is a web app process — there's no
    # terminal for the actual viewer to type into, so the client must
    # never block on input()/getpass() to log in; login instead goes
    # through the form below.
    st.session_state.api_client = LibraryAPIClient()
    st.session_state.api_client.interactive = False

api = st.session_state.api_client

# Bound fresh every script run (Streamlit reruns this whole file top
# to bottom on every interaction): tools.py's tool functions call
# get_api() instead of touching a shared global, so this is what
# makes every tool call during THIS run use THIS session's client —
# see tools.py's own comment for why a contextvar is what makes that
# safe despite tool calls executing on a different thread.
set_api(api)

if "messages" not in st.session_state:
    # Chat history shown in the UI (excludes the system prompt).
    st.session_state.messages = []

if "agent_history" not in st.session_state:
    # Full running message history (including tool calls/results) fed
    # back into every agent.invoke() call so the agent has memory of
    # the conversation. Without this, each turn is a fresh, context-free
    # call and the agent can't follow up on its own questions.
    st.session_state.agent_history = []


# ============================================================
# LOGIN GATE
# ============================================================
# Nothing about this login is persisted anywhere (see api_client.py) —
# every fresh run of this app starts here again.

if not api.is_authenticated:
    st.title("📚 AI Library Assistant")
    st.caption("Log in with your library account to continue.")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

    if submitted:
        try:
            api.login(email, password)
            st.rerun()
        except LibraryAPIError as e:
            st.error(str(e))

    st.stop()


# ============================================================
# MEMBER IDENTITY + PERSISTED MEMORY
# ============================================================
# Everything memory.py does is keyed per member (by email), never
# globally — a shared key/file would leak one member's borrow history
# and conversation into another member's context.

if "member_email" not in st.session_state:
    try:
        # /ai/me responds {"success": true, "data": {..., "email": ...}}
        # — the email is nested under "data", not top-level.
        st.session_state.member_email = api.get_current_user()["data"]["email"]
    except Exception:
        # Same "fails silently" stance as the rest of memory.py: no
        # persistence for this session rather than a broken login.
        st.session_state.member_email = None

if not st.session_state.get("history_loaded"):
    # Only seed from Redis into a genuinely empty session — never
    # overwrite turns that already happened earlier in this same
    # browser session (e.g. a mid-conversation rerun).
    if not st.session_state.messages and not st.session_state.agent_history:
        saved_agent_history, saved_display_messages = memory.load_chat_history(
            st.session_state.member_email
        )
        if saved_agent_history or saved_display_messages:
            st.session_state.agent_history = saved_agent_history
            st.session_state.messages = saved_display_messages
    st.session_state.history_loaded = True


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("📚 AI Library Assistant")
    st.caption("Chat with your library's AI assistant.")

    st.markdown("---")
    st.markdown(f"**Model:** `{OLLAMA_MODEL}`")

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_history = []
        # Resets the Redis-backed session history only — the .md
        # long-term notes file is left intact on purpose (see design
        # discussion: Clear resets the visible chat, not what the
        # agent has learned across all past sessions).
        memory.clear_chat_history(st.session_state.member_email)
        st.rerun()

    if st.button("🚪 Log out", use_container_width=True):
        api.logout()
        st.session_state.messages = []
        st.session_state.agent_history = []
        # Clear identity too, not just chat: otherwise the next login
        # (possibly a different member, same browser tab) would reuse
        # this member's email and load/save into their memory instead.
        st.session_state.member_email = None
        st.session_state.history_loaded = False
        st.rerun()

    with st.expander("System prompt"):
        st.text(SYSTEM_PROMPT.strip())


# ============================================================
# CHAT HISTORY
# ============================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("verified"):
            st.info(message["verified"])
        if message.get("elapsed") is not None:
            st.caption(f"⏱ {message['elapsed']:.2f}s")


# ============================================================
# CHAT INPUT
# ============================================================

user_input = st.chat_input("Ask about books, borrowing, or your account...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    # A real HumanMessage, not a role/content dict: agent_history feeds
    # straight into agent.invoke()'s messages list alongside the
    # BaseMessage objects langgraph returns, and alongside the
    # SystemMessage notes.py prepends each turn — keeping it uniformly
    # list[BaseMessage] avoids mixing message representations in the
    # same list.
    st.session_state.agent_history.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Thinking...")
        try:
            start = time.perf_counter()

            # Final-answer cache: a repeat of the exact same question
            # (light normalization only — trimmed/lowercased, not
            # fuzzy matching) skips agent.invoke() entirely, which is
            # where essentially all the latency lives — the earlier
            # per-tool cache only ever saved the data fetch, which was
            # already fast. Keyed per member: this is what stops a
            # cached personal answer ("what is my name") from ever
            # being replayed to a different member — same reasoning as
            # my_profile's own cache key in tools.py. Never written to
            # for a turn that ran borrow_book/return_book (below) —
            # invalidate_all() also covers this namespace, but a
            # mutating request should just never be answered from
            # cache in the first place, success or failure.
            response_cache_args = {
                "member": st.session_state.member_email,
                "question": user_input.strip().lower(),
            }
            cached_response = get_cached(_RESPONSE_CACHE_TOOL, response_cache_args)

            if cached_response is not None:
                reply = cached_response["reply"]
                verified = cached_response["verified"]
                # No real tool-call trace to replay on a cache hit —
                # append a plain AIMessage so agent_history still
                # reflects that this exchange happened, just without
                # the (already-cached-away) intermediate tool calls.
                st.session_state.agent_history = st.session_state.agent_history + [
                    AIMessage(content=reply)
                ]
            else:
                # Long-term notes are folded in as an extra message for
                # THIS call only — never appended to agent_history itself,
                # or they'd get saved back into the .md file (and Redis)
                # next turn, duplicating a little more on every single
                # turn forever.
                notes_message = memory.notes_as_system_message(
                    memory.load_memory_notes(st.session_state.member_email)
                )
                # Trimmed to the last _MAX_HISTORY_MESSAGES before being
                # sent to the model — agent_history itself, below, stays
                # full. start_on="human" keeps the cut on a clean boundary
                # instead of ever starting mid tool-call/tool-result pair,
                # which some models reject as an invalid message sequence.
                #
                # Left unannotated (bare `list`) on purpose: create_agent's
                # invoke() genuinely accepts a mix of message-like objects
                # (BaseMessage subclasses, role/content dicts) per its own
                # InputAgentState typing (list[AnyMessage | dict[str, Any]])
                # — pinning an element type here just fights that
                # intentionally loose contract for no behavioral gain.
                pending_input: list = trim_messages(
                    st.session_state.agent_history,
                    max_tokens=_MAX_HISTORY_MESSAGES,
                    token_counter=len,
                    strategy="last",
                    start_on="human",
                )
                if notes_message is not None:
                    pending_input = [notes_message] + pending_input
                previous_length = len(pending_input)

                result = agent.invoke({"messages": pending_input})
                new_messages = result["messages"][previous_length:]

                # NOT result["messages"] wholesale — when notes_message was
                # prepended, that would bake the one-off notes message
                # permanently into agent_history. Appending only the new
                # turn's messages onto the existing (notes-free) history
                # keeps that injection transient, as intended.
                st.session_state.agent_history = st.session_state.agent_history + new_messages
                reply = result["messages"][-1].content
                verified = build_verified_block(new_messages)

                # A borrow/return succeeded this turn but the model never
                # (re)called library_stats/my_borrowed_books itself for
                # the rest of the request — don't let its free-hand
                # numbers stand unchecked; go get the real state directly.
                if verified is None and library_state_changed(new_messages):
                    verified = fetch_verified_block()

                mutating_tool_called = any(
                    getattr(msg, "name", None) in _MUTATING_TOOLS for msg in new_messages
                )
                if not mutating_tool_called:
                    set_cached(
                        _RESPONSE_CACHE_TOOL,
                        response_cache_args,
                        {"reply": reply, "verified": verified},
                    )

            elapsed = time.perf_counter() - start
            placeholder.markdown(reply)
            if verified:
                st.info(verified)
            st.caption(f"⏱ {elapsed:.2f}s")
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": reply,
                    "verified": verified,
                    "elapsed": elapsed,
                }
            )

            # Persist this turn: the Redis-backed session history (so
            # a later login/refresh resumes here) and the long-term
            # .md notes (so this Q/A is available as context in every
            # future turn, this session and beyond).
            memory.append_memory_note(st.session_state.member_email, user_input, reply)
            memory.save_chat_history(
                st.session_state.member_email,
                st.session_state.agent_history,
                st.session_state.messages,
            )
        except Exception as e:
            error_text = f"Agent error: {e}"
            placeholder.error(error_text)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_text, "verified": None, "elapsed": None}
            )
