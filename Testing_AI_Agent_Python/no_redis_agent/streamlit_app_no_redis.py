"""
Same Streamlit chat interface as ../langchain_agent/streamlit_app.py,
but wired to agent_no_redis.py (in this same folder, which uses
tools_no_redis.py) — no Redis caching anywhere in this pair. Run side
by side with the others on a different port, e.g. (from the
Testing_AI_Agent_Python directory):

    streamlit run no_redis_agent/streamlit_app_no_redis.py --server.port 8502
"""

import json
import os
import sys
import time

import streamlit as st
from dotenv import load_dotenv

# api_client.py lives one level up (Testing_AI_Agent_Python/), shared
# across every agent folder — see tools_no_redis.py's own comment.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_no_redis import OLLAMA_MODEL, SYSTEM_PROMPT, agent, api
from api_client import LibraryAPIError

load_dotenv()


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


# This is a web app process — there's no terminal for the actual
# viewer to type into, so the API client must never block on
# input()/getpass() to log in. Login instead goes through the form
# below.
api.interactive = False

st.set_page_config(
    page_title="AI Library Assistant (no Redis)",
    page_icon="📚",
    layout="centered",
)


# ============================================================
# SESSION STATE
# ============================================================

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
# `api` is a singleton shared with every tool (see tools_no_redis.py),
# so once it's authenticated here, every tool call in this session
# uses it too. Nothing about this login is persisted anywhere (see
# api_client.py) — every fresh run of this app starts here again.

if not api.is_authenticated:
    st.title("📚 AI Library Assistant (no Redis)")
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
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("📚 AI Library Assistant")
    st.caption("Chat with your library's AI assistant. (no Redis cache)")

    st.markdown("---")
    st.markdown(f"**Model:** `{OLLAMA_MODEL}`")

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_history = []
        st.rerun()

    if st.button("🚪 Log out", use_container_width=True):
        api.logout()
        st.session_state.messages = []
        st.session_state.agent_history = []
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
    st.session_state.agent_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Thinking...")
        try:
            start = time.perf_counter()
            previous_length = len(st.session_state.agent_history)
            result = agent.invoke({"messages": st.session_state.agent_history})
            elapsed = time.perf_counter() - start
            new_messages = result["messages"][previous_length:]
            st.session_state.agent_history = result["messages"]
            reply = result["messages"][-1].content
            verified = build_verified_block(new_messages)

            # A borrow/return succeeded this turn but the model never
            # (re)called library_stats/my_borrowed_books itself for
            # the rest of the request — don't let its free-hand
            # numbers stand unchecked; go get the real state directly.
            if verified is None and library_state_changed(new_messages):
                verified = fetch_verified_block()

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
        except Exception as e:
            error_text = f"Agent error: {e}"
            placeholder.error(error_text)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_text, "verified": None, "elapsed": None}
            )
