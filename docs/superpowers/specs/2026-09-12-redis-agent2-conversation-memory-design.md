# redis_agent2: Conversation Memory (short-term + persistent)

Status: approved for planning
Scope: `Testing_AI_Agent_Python/redis_agent2/` only. Does not touch
`no_redis_agent/`, `redis_agent/`, `langchain_agent/`, or `memory.py`.

## Background

`redis_agent2/` currently is a byte-for-byte copy of `redis_agent/`:
it caches tool-call *results* in Redis and invalidates that cache
correctly on `borrow_book`/`return_book` success, but the agent itself
is stateless — every `invoke_library_agent(user_input)` call starts a
brand-new conversation with no memory of previous turns, and nothing
is persisted anywhere.

Separately, the Laravel backend already has everything needed for
durable, per-member conversation storage:

- Tables `ai_conversations` (`member_id`, `title`) and `ai_messages`
  (`conversation_id`, `role`, `content`).
- `AiConversationController` with `index` (list, scoped to
  `$request->user()->id`), `store` (create), `show` (one, with
  messages, scoped), `destroy` (scoped), `addMessage`.
- Routes under `/api/ai/conversations` (see `routes/api.php`).
- `api_client.py` already has matching methods: `create_conversation`,
  `get_conversations`, `get_conversation`, `delete_conversation`,
  `add_message`, plus `get_current_user()` for the authenticated
  member.

None of this Laravel-side plumbing is wired into `redis_agent2` yet.
This spec covers only that wiring, plus the LangGraph short-term
memory (checkpointer) that sits in front of it. It is sub-project 1 of
a larger plan the user provided; Markdown long-term notes and
LangGraph `Store`/semantic search are explicitly out of scope here and
will get their own design pass later.

## Goals

1. Turn-to-turn memory within a running process: a follow-up question
   ("who wrote the first one?") can refer to the previous turn without
   the caller re-sending history.
2. Conversations survive a process restart: a member can close and
   reopen Streamlit and resume a past conversation with the agent
   actually aware of that history (not just a replayed transcript).
3. A member can see their past conversations, start a new one, and
   delete one, from the Streamlit sidebar.
4. No change to how `no_redis_agent`, `redis_agent`, or `langchain_agent`
   behave.

## Non-goals

- Markdown long-term notes (separate sub-project).
- LangGraph `Store` / semantic search / embeddings (separate
  sub-project).
- Multi-user concurrent access to the same conversation, conversation
  titles/renaming beyond what `store` already accepts, message
  editing/regeneration.
- Persisting anything if the Laravel API is unreachable — this
  degrades to local-only behavior (see Error handling) rather than
  queuing/retrying.

## Architecture

```
Streamlit (redis_agent2/streamlit_app_redis.py)
   │
   ├─ sidebar: list conversations / "New chat" / delete
   │      via conversation_memory.py → Laravel /ai/conversations*
   │
   └─ chat turn: invoke_library_agent(text, thread_id, seed_messages?)
                    │
                    ▼
         agent_redis.py
         (LangChain agent + LangGraph InMemorySaver, keyed by thread_id)
                    │
                    ├─ tool calls ──▶ tools_redis.py (unchanged)
                    │                 ──▶ Redis cache / Laravel library API
                    │
                    └─ after each reply
                         ──▶ conversation_memory.record_turn(...)
                         ──▶ Laravel /ai/conversations/{id}/messages
```

## Components

### `redis_agent2/agent_redis.py` (modified)

- Add `from langgraph.checkpoint.memory import InMemorySaver` and
  `checkpointer = InMemorySaver()`; pass it to `create_agent(...)`.
- `invoke_library_agent` gains two parameters:

  ```python
  def invoke_library_agent(
      user_input: str,
      thread_id: str,
      seed_messages: list[dict] | None = None,
  ) -> dict:
  ```

  Behavior:
  - Maintain a module-level `_seeded_threads: set[str] = set()`.
  - If `thread_id not in _seeded_threads`: build the outgoing
    `messages` list as `(seed_messages or []) + [new user message]`,
    then add `thread_id` to `_seeded_threads`.
  - Else: outgoing `messages` list is just `[new user message]` — the
    checkpointer already holds the rest of this thread's state.
  - Invoke with
    `config={"configurable": {"thread_id": thread_id}}`.
  - `thread_id` is required (no default) — every caller must decide
    which conversation a turn belongs to; there is no implicit
    "default" thread for this module going forward.

- `_seeded_threads` is process-local and intentionally never
  persisted — it only exists to avoid re-seeding the same thread twice
  in one running process. A restart naturally clears it, which is
  correct: the next time that `thread_id` is used in the new process,
  it needs to be re-seeded from Laravel again.

### `redis_agent2/conversation_memory.py` (new)

Thin, fail-soft wrapper around `api_client`'s existing conversation
methods. Every function catches `LibraryAPIError` (and any other
exception from the HTTP layer), prints a `[CONVO] ...` warning to the
console (matching the `[REDIS] ...` convention in `redis_cache.py`),
and returns a safe fallback so the caller never crashes:

```python
def list_conversations() -> list[dict]:
    """Returns [] on failure."""

def start_conversation(title: str | None = None) -> dict | None:
    """Returns the created conversation dict, or None on failure."""

def load_conversation(conversation_id: int) -> list[dict]:
    """
    Returns this conversation's messages as
    [{"role": "user"|"assistant", "content": str}, ...] in order,
    or [] on failure. Only role/content are kept — no tool-call
    detail is stored in Laravel, so none is replayed.
    """

def delete_conversation(conversation_id: int) -> bool:
    """True on success, False on failure."""

def record_turn(conversation_id: int, user_text: str, assistant_text: str) -> None:
    """
    Best-effort: POST the user message, then the assistant message.
    Never raises — a failure here must not interrupt the chat UI.
    """
```

### `redis_agent2/streamlit_app_redis.py` (modified)

Session state additions:
- `conversation_id: int | None`
- `thread_id: str | None` (derived as `f"conv-{conversation_id}"`)
- `pending_seed: list[dict] | None` — set when a conversation is
  (re)loaded, consumed (and cleared) on the very next
  `invoke_library_agent` call.

Sidebar (`st.sidebar`):
- "New chat" button → `start_conversation()` → set
  `conversation_id`/`thread_id`, clear `messages`/`pending_seed`.
- List from `list_conversations()`, most recent first (Laravel's
  `index` already returns `->latest()`), each as a clickable row
  (label falls back to `f"Conversation {id}"` when `title` is null)
  with a small delete (🗑) button next to it.
- Clicking a row (not currently the active one) → `load_conversation(id)`
  → populate `st.session_state.messages` for display AND set
  `pending_seed` to that same list (converted to the dict shape
  `invoke_library_agent` expects) → set `conversation_id`/`thread_id`.
- Clicking delete → `delete_conversation(id)`; if it was the active
  conversation, fall back to "New chat" behavior.
- On first load with no conversation selected: if
  `list_conversations()` is non-empty, auto-select the most recent one
  (same as clicking it); otherwise call `start_conversation()`
  automatically so there's always an active conversation.

Chat turn, once a conversation is active:
1. Append the user message to `st.session_state.messages` (as today).
2. Call
   `invoke_library_agent(user_input, thread_id, seed_messages=pending_seed)`,
   then clear `pending_seed` to `None` regardless of outcome (it must
   only ever be used once per conversation-load).
3. On success, append the assistant message to
   `st.session_state.messages` (as today), then call
   `record_turn(conversation_id, user_input, assistant_text)`
   synchronously.
4. If `conversation_memory` calls fail, show a small
   `st.caption("⚠️ History not saved — Laravel unreachable.")`
   instead of raising; the chat itself keeps working.

## Error handling

- Laravel unreachable at any point (listing, loading, creating,
  deleting, recording): caught inside `conversation_memory.py`,
  logged to console, surfaced to the UI as a small non-blocking
  caption. The chat itself must keep functioning exactly as
  `redis_agent2` does today in that case — worst case, history simply
  isn't listed/saved for that session.
- Agent/tool errors are unaffected by this change and keep behaving as
  they do today.
- `record_turn` runs *after* the assistant message is already shown to
  the user, so a persistence failure never blocks or delays the
  visible reply.

## Testing

- A script analogous to `test_cache.py` (e.g. `test_conversation_memory.py`)
  that:
  1. Calls `invoke_library_agent("List the Python books.", "test-thread")`.
  2. Calls `invoke_library_agent("Who wrote the first one?", "test-thread")`
     and asserts the reply references the earlier answer (this proves
     the checkpointer, not just the wording, is doing the work — no
     history is passed explicitly on the second call).
- A second test that simulates "resume after restart": build a fresh
  `_seeded_threads` state (or just use a new `thread_id`), pass
  `seed_messages` explicitly built from a fake prior exchange, and
  confirm the answer to a single new question is consistent with that
  seeded context.
- Manual Streamlit walkthrough: new chat → ask something → switch away
  and back via sidebar → confirm transcript reloads → ask a follow-up
  that depends on the earlier turn → confirm it's answered correctly
  → delete a conversation → confirm it disappears from the sidebar.

## Open items deferred to later sub-projects

- Markdown long-term per-member notes (adapting `memory.py`).
- LangGraph `Store` + local embeddings + semantic search.
- Smarter, key-specific Redis cache invalidation (current blanket
  `library:*` clear on mutation is kept as-is — already reasonable per
  the user's own plan).
