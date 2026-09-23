"""
Per-member conversation memory: a Redis-backed chat history (so
logging back in resumes the same conversation instead of starting
blank) plus a plain-text .md long-term notes file per member that the
agent re-reads every turn as extra context.

Deliberately split in two, matching two different jobs:
- Redis holds the actual LangChain message objects the agent needs to
  keep replying coherently (HumanMessage/AIMessage/ToolMessage) and
  the parallel UI-only message list Streamlit renders. No TTL is set
  on purpose — kept until clear_chat_history() removes it explicitly.
  This is unrelated to cache.py's own Redis use, which is a *short*
  TTL cache of individual tool-call results, not conversation state.
- The .md file is a plain, human-readable log of every question/answer
  pair, one per member, that's re-read in full and folded into the
  prompt each turn so the agent can refer back to anything discussed
  in ANY past session, not just the current Redis-backed one.

Like cache.py, Redis here is treated as optional infrastructure: every
Redis-backed function fails silently (falls back to "no history") if
Redis isn't reachable, so the agent still works, just without
cross-session persistence, exactly like before this module existed.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    messages_from_dict,
    messages_to_dict,
)

from cache import get_client

_NAMESPACE = "library_agent_memory"

# One .md file per member, held next to this module rather than inside
# langchain_agent/ so it's available to any agent folder later, same
# convention as cache.py/tools.py/api_client.py.
_NOTES_DIR = Path(__file__).parent / "memory"


def _safe_key(member_key: str) -> str:
    """
    Turn an email (or any other member identifier) into something safe
    to use as both a Redis key segment and a filename — lowercased,
    with anything that isn't alphanumeric/._- collapsed to "_".
    """
    return re.sub(r"[^a-zA-Z0-9._-]", "_", member_key.strip().lower())


# ============================================================
# REDIS-BACKED CHAT HISTORY (per member, no expiry)
# ============================================================

def load_chat_history(member_key: str | None) -> tuple[list[BaseMessage], list[dict]]:
    """
    Return (agent_messages, display_messages) previously saved for
    this member, or ([], []) if there's nothing saved yet, Redis is
    unavailable, or member_key is None (e.g. identity lookup failed
    after login) — every public function here accepts None for that
    same reason rather than pushing the check onto every caller.
    """
    client = get_client()
    if client is None or not member_key:
        return [], []

    key = _safe_key(member_key)
    try:
        agent_raw = client.get(f"{_NAMESPACE}:chat:{key}")
        display_raw = client.get(f"{_NAMESPACE}:display:{key}")
    except Exception:
        return [], []

    try:
        agent_messages = messages_from_dict(json.loads(agent_raw)) if agent_raw else []
        display_messages = json.loads(display_raw) if display_raw else []
    except Exception:
        return [], []

    return agent_messages, display_messages


def save_chat_history(
    member_key: str | None,
    agent_messages: list[BaseMessage],
    display_messages: list[dict],
) -> None:
    """
    Persist both message lists for this member. No TTL — history is
    kept until clear_chat_history() removes it explicitly.
    """
    client = get_client()
    if client is None or not member_key:
        return

    key = _safe_key(member_key)
    try:
        client.set(f"{_NAMESPACE}:chat:{key}", json.dumps(messages_to_dict(agent_messages)))
        client.set(f"{_NAMESPACE}:display:{key}", json.dumps(display_messages, default=str))
    except Exception:
        pass


def clear_chat_history(member_key: str | None) -> None:
    """Delete this member's saved Redis chat history (not their .md notes)."""
    client = get_client()
    if client is None or not member_key:
        return

    key = _safe_key(member_key)
    try:
        client.delete(f"{_NAMESPACE}:chat:{key}", f"{_NAMESPACE}:display:{key}")
    except Exception:
        pass


# ============================================================
# LONG-TERM .md NOTES (per member — never expires, never auto-cleared)
# ============================================================

def _notes_path(member_key: str) -> Path:
    return _NOTES_DIR / f"{_safe_key(member_key)}.md"


def load_memory_notes(member_key: str | None, max_entries: int | None = 10) -> str:
    """
    Return this member's accumulated notes file, or "" if none yet.

    max_entries caps how many of the most recent dated Q/A entries are
    returned (default 10) — the file on disk is never touched or
    trimmed by this, only what gets handed back to the caller. Every
    entry is still in the file forever; this just stops the injected
    context from growing without bound as a member's history across
    every past session keeps accumulating. Pass None for the whole
    file untrimmed.
    """
    if not member_key:
        return ""
    path = _notes_path(member_key)
    try:
        content = path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""

    if max_entries is None or not content:
        return content

    # Entries are delimited by a "## <timestamp>" header at the start
    # of a line — split right before each one (keeping the header
    # attached to its entry) and keep only the most recent ones.
    entries = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    entries = [e for e in entries if e.strip()]
    return "".join(entries[-max_entries:])


def append_memory_note(member_key: str | None, question: str, answer: str) -> None:
    """
    Append one dated Q/A entry to this member's notes file, creating
    the memory/ directory and the file itself on first use.
    """
    if not member_key:
        return
    path = _notes_path(member_key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"## {timestamp}\n**Q:** {question}\n**A:** {answer}\n\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def notes_as_system_message(notes: str) -> SystemMessage | None:
    """
    Wrap loaded notes as a one-off SystemMessage for the agent to see
    on this turn only. Callers should prepend the result to the
    message list passed to invoke() WITHOUT saving it back into
    agent_history — otherwise every turn's notes would fold into the
    saved history and get written into the notes file again next
    turn, duplicating forever.
    """
    if not notes:
        return None
    return SystemMessage(
        content=(
            "Long-term notes from this member's earlier conversations "
            "(for reference only — the tools are still the source of "
            "truth for current library data):\n\n" + notes
        )
    )
