# vehicle_agent: Pitstrack fleet-tracking agent

Status: approved for planning
Scope: `Testing_AI_Agent_Python/vehicle_agent/` only. Does not touch
`redis_agent2/`, `no_redis_agent/`, `redis_agent/`, `langchain_agent/`,
or the reference project at
`library-managemant-system-laravel-main/python-agent/` (read-only
source of ported logic, not modified).

## Background

`vehicle_agent/` was created as a byte-for-byte copy of `redis_agent2/`
— it currently answers library questions (books/members/borrowing)
and has no Pitstrack integration at all. The goal is to turn it into a
dedicated fleet-tracking assistant.

A working reference already exists at
`library-managemant-system-laravel-main/python-agent/`: a FastAPI
service whose framework-less agent
(`app/agent/library_agent.py`) talks directly to Ollama's tool-calling
API — deliberately with no intent classifier — and whose
`app/services/pitstrack.py` / `app/tools/pitstrack_data.py` /
`app/agent/tools.py` (`get_vehicles`, `get_working_hours`) already
call the real Pitstrack API (`PITSTRACK_BASE_URL`, default
`https://tracking.dev.pitstrack.com`) correctly. This spec ports that
proven vehicle logic into `vehicle_agent`'s existing LangChain
(`create_agent`) + AI-router structure, rather than adopting the
reference's framework-less style — decided explicitly over the
alternative during brainstorming.

## Goals

1. `vehicle_agent` answers fleet/vehicle questions (listing, filtering,
   sorting, status, count, working hours for a date range) against the
   live Pitstrack API, using the same conversational UX
   (`routed_agent.invoke_routed_agent`, Streamlit chat) as
   `redis_agent2`.
2. A LibrarySystem user still logs in per-user exactly as today
   (`LibraryAPIClient`), and conversation history still persists to
   this app's MySQL via `ConversationMemory` — unchanged. Pitstrack
   access is a second, independent, shared credential (Bearer token +
   account id from environment), never a per-user login.
3. Reuse this project's existing Redis caching (`redis_cache.py`,
   unchanged) for Pitstrack reads, instead of the reference's
   in-process cache — for consistency with the rest of this project.
4. All library-domain code (books/members/borrowing tools, the
   exact-phrase direct-tool fast path, borrowing-history resolution)
   is removed from `vehicle_agent` — this is a vehicle-only agent, not
   a combined one.
5. No change to `redis_agent2/` or any other sibling agent.

## Non-goals

- A combined library+vehicle agent (explicitly rejected during
  brainstorming — vehicle-only was chosen).
- The framework-less/direct-Ollama agent style from the reference
  project (explicitly rejected — keeping `create_agent` + AI router).
- Obtaining or managing the actual `PITSTRACK_TOKEN` — that's a manual
  step on the user's side (Pitstrack has its own login/dashboard; nothing
  in either codebase issues a token). This spec only wires the agent to
  read it from the environment.
- Any deterministic/exact-phrase fast path for vehicle queries (see
  Design: Routing below for why).
- Cache invalidation on write — this domain is read-only, so it isn't
  needed (see Data flow & caching).
- A settings/config module — env vars are read inline via `os.getenv`,
  matching this project's existing convention (`routed_agent.py`'s
  `OLLAMA_MODEL`), not the reference project's `Settings` class.

## Design

### Architecture

```
LibrarySystem user (unchanged login)
        |
        v
vehicle_agent/routed_agent.py: invoke_routed_agent()
        |
        +-- conversation history: MySQL via ConversationMemory (unchanged)
        |
        v
ai_router.classify_route(user_message) -> "vehicles" | "general"
        |
        +-- general  -> general LLM agent, no tools (chit-chat)
        |
        +-- vehicles -> vehicles LLM agent
                             |  get_vehicles / get_working_hours tools
                             v
                      tools_vehicle.py
                             |
                             v
                      PitstrackClient (shared Bearer token + account id)
                             |
                             v
                 https://tracking.dev.pitstrack.com
```

### Components

- **`pitstrack_client.py`** (new) — `PitstrackClient`, ported
  near-verbatim from `app/services/pitstrack.py`: a pooled
  `requests.Session`, `GET /api/vehicles`, `GET
  /api/vehicles/working_hours/[{vehicle_id}]`, `Authorization: Bearer
  <token>` + `selected-account: <id>` headers. Reads
  `PITSTRACK_BASE_URL` (default `https://tracking.dev.pitstrack.com`),
  `PITSTRACK_TOKEN`, `PITSTRACK_ACCOUNT_ID` (default `142`, matching
  the reference), `PITSTRACK_TIMEOUT` (default `15`) via `os.getenv`.
  Raises `PitstrackError` on any HTTP/connection failure, same
  contract as the reference.

- **`tools_vehicle.py`** (new, replaces `tools_redis.py`) —
  `get_vehicles` and `get_working_hours` as LangChain `@tool`s. Ports
  the filter/sort/selection logic from the reference `AgentTools`
  (`_filters`, `_matches`, `_sort_rows`, `_vehicle_view`,
  `_unwrap_model_value`) so the model can filter by field/operator,
  sort, limit, and pick `first`/`random` selection, same as today.
  Response normalization (`_extract`, handling Pitstrack's
  `result.data`/`data`/other wrapper shapes) ports from
  `pitstrack_data.py`. Caching goes through `redis_cache.py`'s
  existing `get_cache`/`set_cache` (unchanged module) instead of the
  reference's in-process TTL cache.

- **`router.py`** — trimmed to `ToolGroup = Literal["vehicles",
  "general"]`. `get_direct_tool`, `resolve_history_tool`,
  `extract_history_target`, and `DIRECT_TOOL_GROUP` are all deleted —
  every one of them is library-specific pattern matching (exact book
  titles, borrow keywords, member/book history disambiguation) with no
  vehicle analogue.

- **`ai_router.py`** — same synonym-tolerant parsing and keyword
  fallback mechanism as `redis_agent2`, narrowed to a binary decision:
  does this message need live fleet data, or not. `AI_ROUTES =
  {"vehicles"}`; anything unparseable still falls back to
  `router_keyword_backup.py`, ported and rewritten with vehicle
  keywords (fleet/vehicle/car/truck/van/tracker/driver/odometer/speed/location,
  etc.) replacing the book/member ones.

- **`prompts/`** — `base_agent.md` reworded for a fleet-tracking
  assistant; new `vehicles_agent.md` (replaces
  `books_agent.md`/`user_agent.md`/`borrowing_agent.md`/`admin_agent.md`)
  describing `get_vehicles`/`get_working_hours` usage, matching the
  reference `SYSTEM_PROMPT`'s guidance (call a tool before answering
  anything that depends on live fleet state; never invent vehicle
  data); `general_agent.md` kept as-is (already domain-agnostic);
  `router.md` rewritten for the vehicles/general split with vehicle
  example phrases.

- **`routed_agent.py`** — rewritten: no `DIRECT_TOOLS` dispatch table
  (nothing to dispatch to — see Routing below), `agents = {"vehicles":
  create_agent(..., tools=[get_vehicles, get_working_hours], ...),
  "general": create_agent(..., tools=[], ...)}`. The response-cache
  mechanism built earlier today for `redis_agent2` is forward-ported
  (`RESPONSE_CACHEABLE_GROUPS = {"vehicles"}`, keys prefixed
  `vehicle:ai_response:...`), along with the `reasoning=True` fix
  (qwen3 needs its thinking step for well-formed tool calls — same
  root cause applies here). `LibraryAPIClient`/`ConversationMemory`
  wiring is untouched.

- **`streamlit_app_routed.py`** — same structure, page title/caption
  and placeholder chat-input text reworded for fleet tracking (e.g.
  "Ask about vehicles, fleet status, or working hours...").

### Routing: why no deterministic fast path

`redis_agent2` has `get_direct_tool()` for exact phrasings like "show
all books" that map 1:1 to a zero-argument tool call. Pitstrack
queries don't have an equivalent: even "show all vehicles" typically
implies default filters/fields the model should still reason about
(and the reference's own prompt explicitly says not to force a fixed
set of question patterns). So `vehicle_agent` sends every message
through `classify_route`, and the `vehicles` agent decides tool
arguments itself, same as the reference implementation does.

### Data flow & caching

- Vehicles list: Redis-cached under key `vehicle:list`, **60s TTL**
  (fleet position/status data goes stale fast — matches the
  reference's own `pitstrack_vehicles_cache_seconds=60`, much shorter
  than the library's 20 min).
- Working hours: Redis-cached per `vehicle:working_hours:{vehicle_id}:
  {start_date}:{end_date}:{unit_id}`, **300s TTL** (historical ranges
  rarely change once queried).
- No invalidation-on-write logic (no `clear_library_cache()`
  equivalent) — this domain is read-only, so TTL alone keeps it
  correct.

### Error handling

- `PitstrackError` (unreachable API, HTTP >= 400, bad JSON) is caught
  at the tool level and returned as a plain error string/dict to the
  model, same pattern as `tools_redis.py`'s `LibraryAPIError` handling
  — the model reports the failure rather than the tool call crashing
  the agent turn.
- Missing `PITSTRACK_TOKEN` is not specially validated at startup;
  the first live call will fail with a clear `PitstrackError` message
  surfaced through the tool, same fail-fast-at-use-time behavior as
  the reference.
- Redis unavailable: falls back to hitting Pitstrack directly every
  time, same fail-open behavior as `redis_cache.py` already
  guarantees elsewhere (no code change needed there).

### Testing

- Unit tests for the ported pure functions (`_filters`, `_matches`,
  `_sort_rows`, `_vehicle_view`, response normalization) — no live API
  or credentials needed.
- `test_pitstrack_client.py` — a manual smoke-test script (style of
  the existing `test_memory.py`) that calls the real Pitstrack API
  once `PITSTRACK_TOKEN`/`PITSTRACK_ACCOUNT_ID` are set, so the user
  can verify their token from Python directly.
- `test_ai_router.py`-equivalent for the vehicles/general binary
  classifier, mirroring the existing one's live-Ollama-call structure
  with vehicle-domain phrasings.

## Open questions for the implementation plan

- Exact list of vehicle fields exposed by default in `_vehicle_view`
  (the reference's default set may need adjusting once real Pitstrack
  data is inspected via the user's own Postman testing).
- Whether `benchmark_final.py`/`benchmark_ai_routing.py`-equivalents
  are worth porting for this agent, or deferred until the domain is
  proven working end-to-end.
