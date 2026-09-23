# Building the Vehicle (Pitstrack) Agent — Step by Step

This walks through every layer needed for an AI agent to answer live
vehicle/fleet questions ("how many vehicles?", "which one is fastest?",
"give me 3 random vehicles") against the Pitstrack API, exactly as it's
built in this project. It covers both agent flavors in this repo — the
plain Ollama tool-calling agent and the LangChain/LangGraph agent — since
they share every layer except how the tool is *described* to the model.

## Architecture at a glance

```
 Model (Ollama / ChatOllama)
        │  decides semantically whether a vehicle question needs data
        ▼
 Tool description                  (what the model sees)
   ├─ Ollama agent:  VEHICLES_TOOL / WORKING_HOURS_TOOL  (raw JSON schema)
   └─ LangChain agent: @tool get_vehicles / get_working_hours (Pydantic)
        │  both call the SAME function underneath
        ▼
 AgentTools.get_vehicles() / get_working_hours()   (business logic)
   filtering, sorting, random sampling, field selection, argument
   normalization — none of this is Pitstrack-specific
        ▼
 PitstrackDataTool                                  (caching + shaping)
   60s in-memory cache, normalizes the API response into flat rows
        ▼
 PitstrackClient                                    (HTTP)
   GET https://tracking.dev.pitstrack.com/api/vehicles
   Authorization: Bearer <token>, selected-account: <id>
        ▼
 Settings (.env)
   PITSTRACK_BASE_URL / PITSTRACK_TOKEN / PITSTRACK_ACCOUNT_ID
```

The point of this layering: **the model never talks to Pitstrack
directly.** It only ever sees a tool description and a JSON result. Every
layer below the tool description is plain, testable Python with no LLM
involved.

---

## Requirements

- **Python** 3.10+ (this project runs on 3.14)
- **Ollama**, running locally, with a tool-calling-capable model pulled
  (this project uses `qwen3:8b`)
- **Packages** (`python-agent/requirements.txt`):
  - Always: `fastapi`, `uvicorn`, `python-dotenv`, `requests`
  - Only for the LangChain agent: `langchain`, `langchain-ollama`,
    `langgraph`, `langgraph-checkpoint-sqlite`
- **A Pitstrack API token** — obtained externally (e.g. via Postman
  against Pitstrack's own login endpoint); this project does not issue
  tokens itself. Note: JWT tokens from this API can be short-lived
  (observed 8-hour expiry) — see Troubleshooting.
- **A `.env` file** in `python-agent/` (copy `.env.example`) with real
  values for the three Pitstrack settings below.

---

## Step 1 — Configuration

Every tunable lives in one place: [`app/config/settings.py`](../app/config/settings.py).

```python
# app/config/settings.py
pitstrack_base_url: str = os.getenv(
    "PITSTRACK_BASE_URL",
    "https://tracking.dev.pitstrack.com",
)

pitstrack_token: str = os.getenv(
    "PITSTRACK_TOKEN",
    "",
).strip()

pitstrack_account_id: str = os.getenv(
    "PITSTRACK_ACCOUNT_ID",
    "142",
).strip()

pitstrack_timeout: int = int(
    os.getenv("PITSTRACK_TIMEOUT", "15")
)

pitstrack_vehicles_cache_seconds: int = int(
    os.getenv("PITSTRACK_VEHICLES_CACHE_SECONDS", "60")
)
```

And in `python-agent/.env`:

```dotenv
PITSTRACK_BASE_URL=https://tracking.dev.pitstrack.com
PITSTRACK_TOKEN=<your real token>
PITSTRACK_ACCOUNT_ID=142
```

Nothing downstream hardcodes a URL, token, or account id — it's all read
through `settings` exactly once at process startup.

---

## Step 2 — HTTP client

[`app/services/pitstrack.py`](../app/services/pitstrack.py) is the only
place that actually calls Pitstrack. It builds the request headers from
settings and raises one typed error (`PitstrackError`) for every failure
mode (HTTP error, network error, bad JSON) so callers don't need to know
`urllib`/`requests` internals.

```python
class PitstrackClient:
    # Shared across every instance/request: Pitstrack is a remote HTTPS
    # host, so a pooled, keep-alive session avoids a fresh TCP+TLS
    # handshake on every lookup.
    _session = requests.Session()

    def __init__(self) -> None:
        self.base_url = settings.pitstrack_base_url.rstrip("/")

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        if settings.pitstrack_token:
            headers["Authorization"] = f"Bearer {settings.pitstrack_token}"
        if settings.pitstrack_account_id:
            headers["selected-account"] = settings.pitstrack_account_id

        try:
            response = self._session.get(
                url, params=params, headers=headers,
                timeout=settings.pitstrack_timeout,
            )
        except requests.RequestException as exc:
            raise PitstrackError(f"Pitstrack unavailable: {exc}") from exc

        if response.status_code >= 400:
            raise PitstrackError(f"Pitstrack HTTP {response.status_code}: {response.text}")

        return response.json() if response.content else {}

    def vehicles(self, page: int | None = None) -> Any:
        return self._request("/api/vehicles", {"page": page} if page is not None else None)

    def working_hours(self, vehicle_id: int, start_date: str, end_date: str,
                       page: int = 1, unit_id: int | None = None) -> Any:
        params = {"start_date": start_date, "end_date": end_date, "page": page}
        if unit_id is not None:
            params["units[0]"] = int(unit_id)
        return self._request(f"/api/vehicles/working_hours/[{int(vehicle_id)}]", params)
```

**Why no `page` param on `vehicles()` by default:** the endpoint already
returns the account's complete dataset in one response; requesting pages
made the upstream API return the same large payload repeatedly and caused
90+ second failures (see the comment in Step 3).

---

## Step 3 — Caching and response shaping

Pitstrack's raw response is a nested `{status, result: {data: [...], total: {...}}}`
shape. [`app/tools/pitstrack_data.py`](../app/tools/pitstrack_data.py)
flattens that into plain rows and caches the vehicle list for 60 seconds
so two consecutive questions (e.g. "max distance" then "top speed") don't
re-download the same payload.

```python
class PitstrackDataTool:
    def __init__(self) -> None:
        self.client = PitstrackClient()
        self._vehicles_cache: list[dict[str, Any]] | None = None
        self._vehicles_cached_at = 0.0

    def vehicles(self, fetch_all: bool = False) -> list[dict[str, Any]]:
        # /api/vehicles already returns the account's complete data set.
        # A short cache avoids downloading the same large payload again
        # for consecutive questions.
        if (
            self._vehicles_cache is not None
            and time.monotonic() - self._vehicles_cached_at
            < settings.pitstrack_vehicles_cache_seconds
        ):
            return self._vehicles_cache

        response = self.client.vehicles()
        rows = self._extract(response)
        self._vehicles_cache, self._vehicles_cached_at = rows, time.monotonic()
        return rows
```

`_extract()` (not reproduced in full here — see the file) defensively
unwraps `result.data`, a bare `data` key, or a handful of other common
wrapper shapes, always falling back to *something* rather than raising, so
an unexpected API response degrades gracefully.

---

## Step 4 — Business logic and safety layer

[`app/agent/tools.py`](../app/agent/tools.py)'s `AgentTools` class is
where filtering, sorting, random sampling, and field selection actually
happen — **in Python, not by asking Pitstrack** (the API has no filter
query params, it just returns everything).

```python
def get_vehicles(self, arguments: dict[str, Any], _: int) -> dict[str, Any]:
    arguments = self._normalize_vehicle_arguments(arguments)
    rows = self.pitstrack.vehicles(fetch_all=True)
    rows = self._filter_rows(rows, self._filters(arguments.get("filters")))
    rows = self._sort_rows(rows, self._sort(arguments.get("sort")))

    matched_count = len(rows)                      # exact total, before limiting
    limit = self._limit(arguments.get("limit"))
    selection = str(arguments.get("selection", "first")).lower()

    if selection == "random":
        shown = secrets.SystemRandom().sample(rows, min(limit, matched_count))
    else:
        shown = rows[:limit]

    return {
        "matched_count": matched_count,
        "selection": selection,
        "records": self._vehicle_view(shown, arguments.get("fields")),
    }
```

Key design points worth keeping if you rebuild this:

- **`matched_count` is always the pre-limit total.** This is what lets
  the model answer "how many vehicles are there?" correctly even though
  only a handful of rows are ever sent back in `records`.
- **`_matches()`** implements the filter operators (`=`, `!=`, `>`, `>=`,
  `<`, `<=`, `like`, `not like`, `in`, `not in`, `is null`, `is not null`)
  against plain dict rows — no SQL, no external query language.
- **`_vehicle_view()`** always keeps `id`/`name` plus either a sane
  default field set or exactly the fields the model asked for, so
  responses stay small and never leak more of the raw record than
  needed.
- **`_normalize_vehicle_arguments` / `_filters` / `_unwrap_model_value`**
  exist because small local models emit slightly-off-but-equivalent JSON
  shapes for the same intent (e.g. `{"speed": {"$gt": 20}}` instead of
  `{"field": "speed", "operator": ">", "value": 20}`). These normalize
  *structure*, never interpret the user's wording — that distinction is
  what keeps this a "no keyword matching" system.
- **`get_working_hours()`** is a thinner pass-through (no filter/sort
  logic) since Pitstrack's working-hours endpoint is already scoped to
  one vehicle and date range.

---

## Step 5 — Describe the tool to the model

This is the **only** step that differs between the two agents in this
repo. Both describe the same capability; only the format differs.

### 5a. Plain Ollama agent — raw JSON schema

[`app/agent/tools.py`](../app/agent/tools.py) — sent as part of the
`tools` array on every Ollama `/api/chat` call:

```python
VEHICLES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_vehicles",
        "description": (
            "Read current Pitstrack vehicle records. Use only for factual, "
            "current vehicle/fleet data. ... Every result includes "
            "matched_count, the exact number before limiting or sampling."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filters": {"type": "array", "items": {"$ref": "#/$defs/filter"}},
                "sort": {"type": "object", "properties": {
                    "field": {"type": "string"},
                    "direction": {"type": "string", "enum": ["asc", "desc"]},
                }, "required": ["field"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "selection": {"type": "string", "enum": ["first", "random"]},
                "fields": {"type": "array", "items": {"type": "string"}},
            },
            "$defs": {"filter": {"type": "object", "properties": {
                "field": {"type": "string"},
                "operator": {"type": "string"},
                "value": {},
            }, "required": ["field", "operator"]}},
        },
    },
}
```

### 5b. LangChain agent — `@tool`-decorated function

[`app/agent/langchain_library_agent.py`](../app/agent/langchain_library_agent.py) —
the exact same capability, described through a type-annotated function
signature instead of a hand-written JSON schema, and delegating straight
to the same `AgentTools` instance:

```python
class FilterArg(BaseModel):
    field: str = Field(description="Column name to filter on.")
    operator: str = Field(description="One of =, !=, >, >=, <, <=, like, ...")
    value: Any = Field(default=None, description="Comparison value.")

class SortArg(BaseModel):
    field: str
    direction: Literal["asc", "desc"] = "asc"

@tool
def get_vehicles(
    runtime: ToolRuntime[AgentContext],          # injected, model never sees this
    filters: list[FilterArg] | None = None,
    sort: SortArg | None = None,
    limit: Annotated[int | None, Field(ge=1, le=50)] = None,
    selection: Literal["first", "random"] = "first",
    fields: list[str] | None = None,
) -> Any:
    """Read current Pitstrack vehicle records.

    Use only for factual, current vehicle/fleet data ... Every result
    includes `matched_count`, the exact number of all matching records
    before limiting or sampling.
    """
    arguments = {
        "filters": _dump_list(filters),
        "sort": _dump(sort),
        "limit": limit,
        "selection": selection,
        "fields": fields,
    }
    return _run_tool(shared, "get_vehicles", arguments, runtime.context["user_id"])
```

`runtime: ToolRuntime[AgentContext]` is how the signed-in `user_id` gets
into the tool call without ever being part of the schema the model can
see or set itself — LangGraph injects it from the `context={"user_id": ...}`
passed to `.invoke()`.

`_run_tool()` wraps the call in a try/except that turns `PitstrackError`
into a plain `{"ok": false, "error": "..."}` result, so a real API failure
(bad token, network issue) becomes an honest answer instead of a crash:

```python
def _run_tool(shared: AgentTools, name: str, arguments: dict[str, Any], user_id: int) -> Any:
    try:
        result = shared.execute(name, arguments, user_id)
    except PitstrackError:
        return {"ok": False, "error": "The vehicle data source is currently unavailable."}
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": f"Invalid tool arguments: {exc}"}
    except Exception:
        return {"ok": False, "error": "The requested data operation could not be completed."}
    return {"ok": True, "data": result}
```

---

## Step 6 — Wire the tool into the agent loop

**Plain Ollama agent** ([`app/agent/library_agent.py`](../app/agent/library_agent.py)):
`TOOLS` (the list including `VEHICLES_TOOL`) is sent with every chat
request; the system prompt tells the model *when* live data is needed but
never which keywords to look for — tool choice is entirely the model's.

```python
payload = {
    "model": settings.ollama_model,
    "messages": messages,
    "tools": TOOLS,
    "think": False,
    "options": {"temperature": 0, ...},
}
```

**LangChain agent** ([`app/agent/langchain_library_agent.py`](../app/agent/langchain_library_agent.py)):
tools are passed straight to `create_agent`, which runs the whole
model/tool loop internally (built on LangGraph):

```python
self._graph = create_agent(
    model=ChatOllama(model=settings.ollama_model, temperature=0, ...),
    tools=build_tools(self.tools),      # includes get_vehicles, get_working_hours
    system_prompt=SYSTEM_PROMPT,        # imported, not duplicated
    checkpointer=self._checkpointer,    # per-user memory
    context_schema=AgentContext,
)
```

---

## Step 7 — Expose it over HTTP

[`main.py`](../main.py) exposes both agents behind the same contract:

```python
@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest, _: None = Depends(verify_local_access)) -> ChatResponse:
    return ChatResponse(**agent.chat(request.message, request.user_id))

@app.post("/api/v2/chat", response_model=ChatResponse)
def chat_langchain(request: ChatRequest, _: None = Depends(verify_local_access)) -> ChatResponse:
    return ChatResponse(**langchain_agent.chat(request.message, request.user_id))
```

Auth is a static shared secret header, checked locally — it never calls
out to Laravel or Pitstrack:

```python
def verify_local_access(x_api_secret: str = Header(default="")) -> None:
    if x_api_secret != settings.api_secret:
        raise HTTPException(status_code=401, detail="Unauthorized local agent request.")
```

---

## Step 8 — Run and test it

**Start the API:**

```powershell
cd python-agent
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

**Test the raw Pitstrack call in Postman** (bypasses the agent entirely —
good first check when something's wrong):

- `GET https://tracking.dev.pitstrack.com/api/vehicles`
- Headers: `Accept: application/json`, `Authorization: Bearer <token>`,
  `selected-account: 142`

**Test the agent via Postman:**

- `POST http://127.0.0.1:8001/api/v2/chat`
- Headers: `Content-Type: application/json`, `X-Api-Secret: <PYTHON_AGENT_SECRET>`
- Body: `{"message": "how many vehicles are in the fleet?", "user_id": 1}`

**Or test interactively with the Streamlit console:**

```powershell
cd python-agent
python -m streamlit run streamlit_app.py
```

Sample queries to exercise every code path — count, list, filter, sort,
random sample, specific fields, and a two-turn working-hours lookup:

1. `how many vehicles are in the fleet?`
2. `list 5 vehicles`
3. `show vehicles with speed greater than 60`
4. `which vehicle has the highest odometer?`
5. `give me 3 random vehicles`
6. `what's the driver name and speed for each vehicle?`
7. `what's vehicle 12's status?` → then `how many working hours did it log between 2026-09-01 and 2026-09-15?`

---

## Troubleshooting

- **`{"ok": false, "error": "The vehicle data source is currently unavailable."}`**
  every time → check the token first. Decode it locally (no network call
  needed) to check expiry:

  ```python
  import base64, json, time
  payload = token.split(".")[1]
  payload += "=" * (-len(payload) % 4)
  data = json.loads(base64.urlsafe_b64decode(payload))
  print("expired:", time.time() > data.get("exp", 0))
  ```

  Pitstrack JWTs observed in this project expire ~8 hours after issue —
  short enough that you'll likely need to refresh it every test session.

- **Very slow responses (30s–200s+) even on success** → this is Ollama
  running the model on CPU, not the Pitstrack call (a 401 from Pitstrack
  itself returns in well under a second). Check `ollama ps` — if
  `size_vram` is `0` for your model, it's running entirely on CPU.

- **No `.env` file** → `settings.py` silently falls back to
  `PITSTRACK_TOKEN=""`, which will always fail auth. Copy
  `.env.example` to `.env` and fill in real values; restart the process
  afterward, since settings are only read once at startup.
