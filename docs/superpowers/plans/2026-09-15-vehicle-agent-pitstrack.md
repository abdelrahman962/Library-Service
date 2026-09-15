# vehicle_agent Pitstrack Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `vehicle_agent/` (currently an untouched copy of `redis_agent2/`) into a dedicated fleet-tracking assistant that answers vehicle/working-hours questions against the live Pitstrack API, using the same conversational architecture (LangChain `create_agent`, AI router, Redis caching, MySQL-backed conversation memory) as its sibling.

**Architecture:** A LibrarySystem user still logs in per-user via `LibraryAPIClient` (conversation history unchanged, MySQL via `ConversationMemory`). `ai_router.classify_route` picks `"vehicles"` or `"general"` per message; `"vehicles"` dispatches to a LangChain agent holding two tools (`get_vehicles`, `get_working_hours`) backed by a new `PitstrackClient` (a second, independent, shared-token credential — not per-user). All library-domain tools/prompts/routing are deleted, not adapted.

**Tech Stack:** Python, `langchain`/`langchain_ollama` (`create_agent`, `ChatOllama`), `requests` (Pitstrack HTTP), existing `redis_cache.py` (unchanged), existing `conversation_memory.py`/`LibraryAPIClient` (unchanged), plain assert-based test scripts (no pytest — matches this codebase's existing convention; verified absent from `requirements.txt`/venv).

**Spec:** `docs/superpowers/specs/2026-09-15-vehicle-agent-pitstrack-design.md`

## Global Constraints

- Scope is `Testing_AI_Agent_Python/vehicle_agent/` only. Never edit `redis_agent2/`, `no_redis_agent/`, `redis_agent/`, `langchain_agent/`, or the reference project at `library-managemant-system-laravel-main/python-agent/` (read-only source of ported logic).
- Pitstrack env vars, read via `os.getenv` inline (no settings module, matching this project's existing style): `PITSTRACK_BASE_URL` (default `https://tracking.dev.pitstrack.com`), `PITSTRACK_TOKEN` (default `""`), `PITSTRACK_ACCOUNT_ID` (default `"142"`), `PITSTRACK_TIMEOUT` (default `15`).
- No per-user Pitstrack auth. `LibraryAPIClient`/`ConversationMemory` wiring for identity and history stays exactly as in `redis_agent2`.
- Reuse `redis_cache.py` unchanged (`get_cache`/`set_cache`, fail-open on Redis being down).
- No cache invalidation-on-write — this domain is read-only, so TTL alone (vehicles list: 60s, working hours: 300s) keeps it correct.
- No deterministic/exact-phrase fast path (no `get_direct_tool` equivalent) — every message goes through `classify_route`.
- Test files are plain scripts with `assert` + a print-based PASS/FAIL runner (matching `redis_agent2/test_ai_router.py`), run via `python test_x.py` — **not** pytest.
- Response cache (ported from today's `redis_agent2` work): `RESPONSE_CACHEABLE_GROUPS = {"vehicles"}`, keys prefixed `vehicle:ai_response:`, 300s TTL.

## File Structure

```
vehicle_agent/
├── pitstrack_client.py          [NEW]  PitstrackClient, PitstrackError
├── test_pitstrack_client_unit.py [NEW]  mocked unit tests for pitstrack_client.py
├── test_pitstrack_client.py     [REWRITE] live smoke-test script (needs real PITSTRACK_TOKEN)
├── tools_vehicle.py             [NEW]  get_vehicles/get_working_hours tools + helpers
├── test_tools_vehicle.py        [NEW]  unit tests for tools_vehicle.py
├── tools_redis.py               [DELETE]
├── agent_redis.py               [DELETE]
├── streamlit_app_redis.py       [DELETE]
├── router.py                    [REWRITE] trimmed to ToolGroup + nothing else
├── router_keyword_backup.py     [REWRITE] vehicle keywords
├── test_router_keyword_backup.py [NEW]
├── ai_router.py                 [MODIFY] AI_ROUTES = {"vehicles"}, vehicle synonyms
├── test_ai_router.py            [REWRITE] vehicle-domain live test cases
├── routed_agent.py              [REWRITE] two groups, no direct-tool dispatch
├── streamlit_app_routed.py      [MODIFY] relabeled for fleet tracking
├── prompts/
│   ├── base_agent.md            [REWRITE]
│   ├── vehicles_agent.md        [NEW]
│   ├── general_agent.md         [KEEP as-is, verified generic]
│   ├── router.md                [REWRITE]
│   ├── books_agent.md           [DELETE]
│   ├── user_agent.md            [DELETE]
│   ├── borrowing_agent.md       [DELETE]
│   └── admin_agent.md           [DELETE]
├── redis_cache.py               [UNCHANGED]
├── conversation_memory.py       [UNCHANGED]
└── (benchmark_*.py, session_memory.py, memory_retrieval.py,
     test_memory.py, test_recent_memory.py, test_conversation_api.py)
                                  [UNCHANGED - out of scope per spec's
                                   deferred open question; some
                                   benchmark files will reference
                                   deleted modules and are expected to
                                   be broken until a future pass ports
                                   them]
```

---

### Task 1: Repo cleanup — remove library-only files

**Files:**
- Delete: `Testing_AI_Agent_Python/vehicle_agent/tools_redis.py`
- Delete: `Testing_AI_Agent_Python/vehicle_agent/agent_redis.py`
- Delete: `Testing_AI_Agent_Python/vehicle_agent/streamlit_app_redis.py`
- Delete: `Testing_AI_Agent_Python/vehicle_agent/prompts/books_agent.md`
- Delete: `Testing_AI_Agent_Python/vehicle_agent/prompts/user_agent.md`
- Delete: `Testing_AI_Agent_Python/vehicle_agent/prompts/borrowing_agent.md`
- Delete: `Testing_AI_Agent_Python/vehicle_agent/prompts/admin_agent.md`

**Interfaces:**
- Produces: a clean `vehicle_agent/` with no library-domain tool/prompt files, ready for Tasks 2+ to build on.

- [ ] **Step 1: Delete the files**

```bash
cd "Testing_AI_Agent_Python/vehicle_agent"
rm tools_redis.py agent_redis.py streamlit_app_redis.py
rm prompts/books_agent.md prompts/user_agent.md prompts/borrowing_agent.md prompts/admin_agent.md
```

- [ ] **Step 2: Verify nothing outside the known-deferred benchmark files still references them**

```bash
grep -rl "tools_redis\|agent_redis\|streamlit_app_redis" *.py
```

Expected output: only `benchmark_routing.py` and `benchmark_routing_v2.py` (these are explicitly deferred per the spec's open question — leave them broken/unported, do not fix them in this plan). If any *other* file appears, stop and investigate before continuing — it means something in scope still depends on deleted code.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "vehicle_agent: remove library-domain-only files

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: PitstrackClient

**Files:**
- Create: `Testing_AI_Agent_Python/vehicle_agent/pitstrack_client.py`
- Test: `Testing_AI_Agent_Python/vehicle_agent/test_pitstrack_client_unit.py`

**Interfaces:**
- Produces: `class PitstrackClient` with `.vehicles(page=None) -> Any` and `.working_hours(vehicle_id: int, start_date: str, end_date: str, page: int = 1, unit_id: int | None = None) -> Any`; `class PitstrackError(RuntimeError)`. Both raise `PitstrackError` on any HTTP/connection/JSON failure. Later tasks (`tools_vehicle.py`) construct `PitstrackClient()` directly (no per-user auth, so no `set_client`/`get_client` indirection needed).

- [ ] **Step 1: Write the failing test**

Create `Testing_AI_Agent_Python/vehicle_agent/test_pitstrack_client_unit.py`:

```python
"""
Unit tests for PitstrackClient - mocked HTTP, no live Pitstrack API or
token needed. For a live check against the real API, see
test_pitstrack_client.py instead.
"""

import os
from unittest.mock import MagicMock, patch

import requests

from pitstrack_client import PitstrackClient, PitstrackError


def _fake_response(status_code=200, json_data=None, text="", content=b"{}"):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.content = content
    response.json.return_value = json_data if json_data is not None else {}
    return response


def test_vehicles_sends_correct_url_and_headers():
    os.environ["PITSTRACK_BASE_URL"] = "https://tracking.dev.pitstrack.com"
    os.environ["PITSTRACK_TOKEN"] = "test-token"
    os.environ["PITSTRACK_ACCOUNT_ID"] = "99"

    client = PitstrackClient()

    with patch.object(
        client._session,
        "get",
        return_value=_fake_response(json_data={"result": {"data": []}}),
    ) as mock_get:
        client.vehicles()

    args, kwargs = mock_get.call_args
    assert args[0] == "https://tracking.dev.pitstrack.com/api/vehicles", args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert kwargs["headers"]["selected-account"] == "99"


def test_http_error_raises_pitstrack_error():
    client = PitstrackClient()

    with patch.object(
        client._session,
        "get",
        return_value=_fake_response(status_code=401, text="Unauthorized"),
    ):
        try:
            client.vehicles()
        except PitstrackError as e:
            assert "401" in str(e), str(e)
        else:
            raise AssertionError("Expected PitstrackError")


def test_connection_error_raises_pitstrack_error():
    client = PitstrackClient()

    with patch.object(
        client._session,
        "get",
        side_effect=requests.ConnectionError("refused"),
    ):
        try:
            client.vehicles()
        except PitstrackError as e:
            assert "unavailable" in str(e), str(e)
        else:
            raise AssertionError("Expected PitstrackError")


def test_working_hours_builds_correct_path_and_params():
    client = PitstrackClient()

    with patch.object(
        client._session,
        "get",
        return_value=_fake_response(json_data={"result": {"data": []}}),
    ) as mock_get:
        client.working_hours(
            vehicle_id=42,
            start_date="2026-01-01",
            end_date="2026-01-31",
            unit_id=7,
        )

    args, kwargs = mock_get.call_args
    expected_path = "https://tracking.dev.pitstrack.com/api/vehicles/working_hours/[42]"
    assert args[0] == expected_path, args[0]
    assert kwargs["params"]["start_date"] == "2026-01-01"
    assert kwargs["params"]["end_date"] == "2026-01-31"
    assert kwargs["params"]["units[0]"] == 7


def test_empty_body_returns_empty_dict():
    client = PitstrackClient()

    with patch.object(
        client._session,
        "get",
        return_value=_fake_response(content=b""),
    ):
        result = client.vehicles()

    assert result == {}


TESTS = [
    test_vehicles_sends_correct_url_and_headers,
    test_http_error_raises_pitstrack_error,
    test_connection_error_raises_pitstrack_error,
    test_working_hours_builds_correct_path_and_params,
    test_empty_body_returns_empty_dict,
]


def main():
    passed = 0
    failed = 0

    for test in TESTS:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} passed")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "Testing_AI_Agent_Python/vehicle_agent"
python test_pitstrack_client_unit.py
```

Expected: `ModuleNotFoundError: No module named 'pitstrack_client'`.

- [ ] **Step 3: Write the implementation**

Create `Testing_AI_Agent_Python/vehicle_agent/pitstrack_client.py`:

```python
"""
Thin HTTP client for the Pitstrack fleet-tracking API.

Pitstrack is a single shared account, not a per-user login: every
request uses the same PITSTRACK_TOKEN/PITSTRACK_ACCOUNT_ID from the
environment, regardless of which LibrarySystem user is chatting. This
is independent of LibraryAPIClient's per-user auth.
"""

import os
from typing import Any

import requests


class PitstrackError(RuntimeError):
    pass


class PitstrackClient:

    # Shared across every instance: Pitstrack is a remote HTTPS host,
    # so reusing a pooled, keep-alive session avoids a fresh TCP+TLS
    # handshake on every vehicle or working-hours lookup.
    _session = requests.Session()

    def __init__(self) -> None:

        self.base_url = os.getenv(
            "PITSTRACK_BASE_URL",
            "https://tracking.dev.pitstrack.com",
        ).rstrip("/")

        self.token = os.getenv("PITSTRACK_TOKEN", "").strip()
        self.account_id = os.getenv("PITSTRACK_ACCOUNT_ID", "142").strip()
        self.timeout = int(os.getenv("PITSTRACK_TIMEOUT", "15"))

    def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:

        url = f"{self.base_url}{path}"

        headers = {"Accept": "application/json"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        if self.account_id:
            headers["selected-account"] = self.account_id

        try:
            response = self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PitstrackError(f"Pitstrack unavailable: {exc}") from exc

        if response.status_code >= 400:
            raise PitstrackError(
                f"Pitstrack HTTP {response.status_code}: {response.text}"
            )

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:
            raise PitstrackError(f"Pitstrack request failed: {exc}") from exc

    def vehicles(self, page: int | None = None) -> Any:

        return self._request(
            "/api/vehicles",
            {"page": page} if page is not None else None,
        )

    def working_hours(
        self,
        vehicle_id: int,
        start_date: str,
        end_date: str,
        page: int = 1,
        unit_id: int | None = None,
    ) -> Any:

        params: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
        }

        if unit_id is not None:
            params["units[0]"] = int(unit_id)

        path = f"/api/vehicles/working_hours/[{int(vehicle_id)}]"

        return self._request(path, params)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python test_pitstrack_client_unit.py
```

Expected: `5/5 passed`.

- [ ] **Step 5: Commit**

```bash
git add pitstrack_client.py test_pitstrack_client_unit.py
git commit -m "vehicle_agent: add PitstrackClient with mocked unit tests

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Live Pitstrack smoke-test script

**Files:**
- Rewrite: `Testing_AI_Agent_Python/vehicle_agent/test_pitstrack_client.py` (currently a stale library-domain conversation test copied from `redis_agent2` — replace its content entirely)

**Interfaces:**
- Consumes: `PitstrackClient` from Task 2.
- Produces: a manual script the user runs once they have a real `PITSTRACK_TOKEN` set, to confirm it from Python directly (not just Postman).

- [ ] **Step 1: Write the script**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/test_pitstrack_client.py`:

```python
"""
Live smoke test against the real Pitstrack API.

Requires PITSTRACK_TOKEN (and usually PITSTRACK_ACCOUNT_ID) to be set
in the environment first - this is NOT a mocked test, see
test_pitstrack_client_unit.py for that. Run manually:

    python test_pitstrack_client.py
"""

import os

from pitstrack_client import PitstrackClient, PitstrackError


def main():
    print("=== Pitstrack Live Smoke Test ===\n")

    if not os.getenv("PITSTRACK_TOKEN", "").strip():
        print(
            "PITSTRACK_TOKEN is not set. Set it (and PITSTRACK_ACCOUNT_ID "
            "if your account id isn't the default) before running this "
            "script, e.g.:\n"
            "  set PITSTRACK_TOKEN=your-token-here   (PowerShell: $env:PITSTRACK_TOKEN=...)\n"
        )
        return

    client = PitstrackClient()
    print(f"Base URL:   {client.base_url}")
    print(f"Account id: {client.account_id}\n")

    try:
        response = client.vehicles()
    except PitstrackError as e:
        print(f"FAILED: {e}")
        return

    print("Raw response keys:", list(response.keys()) if isinstance(response, dict) else type(response))
    print("\nFull first-level response (truncated to 2000 chars):")
    print(str(response)[:2000])
    print("\n=== Smoke test completed - inspect the shape above ===")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it once (token not set yet — expect the graceful message)**

```bash
python test_pitstrack_client.py
```

Expected: prints the "PITSTRACK_TOKEN is not set" message and exits cleanly (no traceback). This confirms the script itself works correctly even before a real token exists. Once the user has a token (from their own Postman verification), re-running this with `PITSTRACK_TOKEN` set should print real vehicle data instead — that re-run is on the user, not part of this automated step.

- [ ] **Step 3: Commit**

```bash
git add test_pitstrack_client.py
git commit -m "vehicle_agent: replace stale conversation test with Pitstrack live smoke test

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Pure response/filter/sort helpers in tools_vehicle.py

**Files:**
- Create: `Testing_AI_Agent_Python/vehicle_agent/tools_vehicle.py` (helpers only this task — no `@tool` functions yet, those are Task 5)
- Test: `Testing_AI_Agent_Python/vehicle_agent/test_tools_vehicle.py`

**Interfaces:**
- Produces: `_extract(response, include_total=False) -> list[dict]`, `_matches(row, condition) -> bool`, `_filter_rows(rows, filters) -> list[dict]`, `_sort_rows(rows, sort) -> list[dict]`, `_vehicle_view(rows) -> list[dict]`, `DEFAULT_VEHICLE_FIELDS`. Task 5 builds `get_vehicles`/`get_working_hours` on top of these.
- Note: the reference implementation's `_filters()` (which tolerates many raw-JSON shapes a *framework-less* model might emit) is deliberately **not** ported — this design gives the LangChain-wired model typed keyword arguments instead of a free-form filter JSON, so that model-output-tolerance layer no longer applies. Only the filter-*evaluation* engine (`_matches`/`_filter_rows`) is needed.

- [ ] **Step 1: Write the failing test**

Create `Testing_AI_Agent_Python/vehicle_agent/test_tools_vehicle.py`:

```python
"""
Unit tests for the pure helpers in tools_vehicle.py - no live Pitstrack
API, no Redis needed.
"""

from tools_vehicle import (
    _extract,
    _matches,
    _filter_rows,
    _sort_rows,
    _vehicle_view,
)


def test_extract_result_data_shape():
    response = {
        "status": "success",
        "result": {
            "data": [{"id": 1, "name": "Truck A"}, {"id": 2, "name": "Van B"}],
            "total": {"count": 2},
        },
    }
    rows = _extract(response)
    assert rows == [{"id": 1, "name": "Truck A"}, {"id": 2, "name": "Van B"}], rows


def test_extract_result_data_with_total_summary():
    response = {
        "result": {
            "data": [{"id": 1}],
            "total": {"hours": 40},
        },
    }
    rows = _extract(response, include_total=True)
    assert len(rows) == 2, rows
    assert rows[-1] == {"__summary__": True, "hours": 40}, rows[-1]


def test_extract_direct_data_list():
    response = {"data": [{"id": 5}]}
    assert _extract(response) == [{"id": 5}]


def test_extract_other_wrapper_key():
    response = {"vehicles": [{"id": 9}]}
    assert _extract(response) == [{"id": 9}]


def test_extract_non_dict_scalar():
    assert _extract("oops") == [{"value": "oops"}]


def test_extract_plain_list():
    assert _extract([{"id": 1}, "x"]) == [{"id": 1}, {"value": "x"}]


def test_matches_equality_and_numeric_operators():
    row = {"speed": "45", "status": "moving"}
    assert _matches(row, {"field": "status", "operator": "=", "value": "moving"})
    assert not _matches(row, {"field": "status", "operator": "=", "value": "idle"})
    assert _matches(row, {"field": "speed", "operator": ">=", "value": 40})
    assert not _matches(row, {"field": "speed", "operator": ">", "value": 100})


def test_matches_like_and_null():
    row = {"driver_name": "Omar Amjad", "note": None}
    assert _matches(row, {"field": "driver_name", "operator": "like", "value": "omar"})
    assert _matches(row, {"field": "note", "operator": "is null"})
    assert not _matches(row, {"field": "note", "operator": "is not null"})


def test_filter_rows_all_must_match():
    rows = [
        {"status": "moving", "speed": "50"},
        {"status": "moving", "speed": "10"},
        {"status": "idle", "speed": "0"},
    ]
    filters = [
        {"field": "status", "operator": "=", "value": "moving"},
        {"field": "speed", "operator": ">=", "value": 20},
    ]
    result = _filter_rows(rows, filters)
    assert result == [{"status": "moving", "speed": "50"}], result


def test_sort_rows_numeric_desc_puts_missing_last():
    rows = [
        {"name": "A", "speed": "10"},
        {"name": "B", "speed": "90"},
        {"name": "C", "speed": None},
    ]
    result = _sort_rows(rows, {"field": "speed", "direction": "desc"})
    assert [row["name"] for row in result] == ["B", "A", "C"], result


def test_sort_rows_text_ascending():
    rows = [{"name": "Van"}, {"name": "Bus"}, {"name": "car"}]
    result = _sort_rows(rows, {"field": "name", "direction": "asc"})
    assert [row["name"] for row in result] == ["Bus", "car", "Van"], result


def test_sort_rows_no_sort_returns_unchanged():
    rows = [{"name": "A"}, {"name": "B"}]
    assert _sort_rows(rows, None) == rows


def test_vehicle_view_only_known_fields():
    rows = [{"id": 1, "name": "Truck A", "secret_internal_field": "x", "speed": 30}]
    view = _vehicle_view(rows)
    assert view == [{"id": 1, "name": "Truck A", "speed": 30}], view


TESTS = [
    test_extract_result_data_shape,
    test_extract_result_data_with_total_summary,
    test_extract_direct_data_list,
    test_extract_other_wrapper_key,
    test_extract_non_dict_scalar,
    test_extract_plain_list,
    test_matches_equality_and_numeric_operators,
    test_matches_like_and_null,
    test_filter_rows_all_must_match,
    test_sort_rows_numeric_desc_puts_missing_last,
    test_sort_rows_text_ascending,
    test_sort_rows_no_sort_returns_unchanged,
    test_vehicle_view_only_known_fields,
]


def main():
    passed = 0
    failed = 0

    for test in TESTS:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} passed")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python test_tools_vehicle.py
```

Expected: `ModuleNotFoundError: No module named 'tools_vehicle'`.

- [ ] **Step 3: Write the implementation**

Create `Testing_AI_Agent_Python/vehicle_agent/tools_vehicle.py`:

```python
"""
Pitstrack vehicle tools for the LangChain agent.

Response normalization (_extract) is ported from the reference
python-agent's app/tools/pitstrack_data.py. The filter-evaluation
engine (_matches/_filter_rows) and numeric-aware sort (_sort_rows) are
ported from app/agent/tools.py's AgentTools. The reference's raw-JSON
filter *parsing* tolerance layer (_filters/_unwrap_model_value) is
deliberately not ported: get_vehicles below gives the model typed
keyword arguments instead of a free-form filter JSON, so there is
nothing to tolerate-parse.
"""

import math
from typing import Any


# =========================================================
# Response normalization
# =========================================================

def _extract(
    response: Any,
    include_total: bool = False,
) -> list[dict[str, Any]]:

    if isinstance(response, list):
        return [
            row if isinstance(row, dict) else {"value": row}
            for row in response
        ]

    if not isinstance(response, dict):
        return [{"value": response}]

    # Pitstrack: {status, result: {data: [...], total: {...}}}
    result = response.get("result")

    if isinstance(result, dict):
        data = result.get("data")

        if isinstance(data, list):
            rows = [
                row if isinstance(row, dict) else {"value": row}
                for row in data
            ]

            if include_total:
                total = result.get("total")

                if isinstance(total, dict):
                    rows.append({"__summary__": True, **total})

            return rows

    data = response.get("data")

    if isinstance(data, list):
        return [
            row if isinstance(row, dict) else {"value": row}
            for row in data
        ]

    for key in ("vehicles", "results", "items", "working_hours"):

        value = response.get(key)

        if isinstance(value, list):
            return [
                row if isinstance(row, dict) else {"value": row}
                for row in value
            ]

    return [response]


# =========================================================
# Filter evaluation
# =========================================================

def _matches(row: dict[str, Any], condition: dict[str, Any]) -> bool:

    field = str(condition.get("field", ""))
    operator = str(condition.get("operator", "=")).strip().lower()
    expected = condition.get("value")
    actual = row.get(field)

    if operator == "is null":
        return actual is None

    if operator == "is not null":
        return actual is not None

    if operator in {"in", "not in"}:
        if not isinstance(expected, list):
            return False
        matched = actual in expected
        return not matched if operator == "not in" else matched

    if operator in {"like", "not like"}:
        matched = str(expected or "").lower() in str(actual or "").lower()
        return not matched if operator == "not like" else matched

    if operator in {">", ">=", "<", "<="}:
        if actual is None or expected is None:
            return False
        try:
            left, right = float(actual), float(expected)
        except (TypeError, ValueError):
            return False
        return {
            ">": left > right,
            ">=": left >= right,
            "<": left < right,
            "<=": left <= right,
        }[operator]

    if operator in {"=", "=="}:
        return (
            actual == expected
            or str(actual).lower() == str(expected).lower()
        )

    if operator in {"!=", "<>"}:
        return not _matches(row, {**condition, "operator": "="})

    return False


def _filter_rows(
    rows: list[dict[str, Any]],
    filters: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    return [
        row
        for row in rows
        if isinstance(row, dict) and all(_matches(row, f) for f in filters)
    ]


# =========================================================
# Sorting
# =========================================================

def _sort_rows(
    rows: list[dict[str, Any]],
    sort: dict[str, str] | None,
) -> list[dict[str, Any]]:

    if not sort:
        return rows

    field = sort["field"]

    numeric_rows: list[tuple[dict[str, Any], float]] = []
    text_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []

    for row in rows:
        value = row.get(field)

        if value is None or str(value).strip() in {"", "-"}:
            missing_rows.append(row)
            continue

        try:
            number = float(value)
            if math.isfinite(number):
                numeric_rows.append((row, number))
                continue
        except (TypeError, ValueError):
            pass

        text_rows.append(row)

    if numeric_rows:
        ordered_numeric = sorted(
            numeric_rows,
            key=lambda item: item[1],
            reverse=sort["direction"] == "desc",
        )
        return [row for row, _ in ordered_numeric] + text_rows + missing_rows

    return sorted(
        text_rows,
        key=lambda row: str(row.get(field) or "").lower(),
        reverse=sort["direction"] == "desc",
    ) + missing_rows


# =========================================================
# Output shaping
# =========================================================

DEFAULT_VEHICLE_FIELDS = (
    "id", "name", "vehicle_type", "manufacturer", "model",
    "vehicle_status", "driver_name", "odometer", "speed", "device_number",
)


def _vehicle_view(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:

    return [
        {
            field: row.get(field)
            for field in DEFAULT_VEHICLE_FIELDS
            if field in row
        }
        for row in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python test_tools_vehicle.py
```

Expected: `13/13 passed`.

- [ ] **Step 5: Commit**

```bash
git add tools_vehicle.py test_tools_vehicle.py
git commit -m "vehicle_agent: add pure response/filter/sort helpers to tools_vehicle.py

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: get_vehicles / get_working_hours tools with Redis caching

**Files:**
- Modify: `Testing_AI_Agent_Python/vehicle_agent/tools_vehicle.py` (add to the file from Task 4)
- Modify: `Testing_AI_Agent_Python/vehicle_agent/test_tools_vehicle.py` (extend)

**Interfaces:**
- Consumes: `_extract`, `_filter_rows`, `_sort_rows`, `_vehicle_view` (Task 4); `PitstrackClient`, `PitstrackError` (Task 2); `get_cache`, `set_cache` (existing `redis_cache.py`, unchanged).
- Produces: `get_vehicles` and `get_working_hours` — LangChain `@tool`-decorated functions returning formatted strings. Task 10 (`routed_agent.py`) imports both by name.

- [ ] **Step 1: Write the failing test**

Append to `Testing_AI_Agent_Python/vehicle_agent/test_tools_vehicle.py` — add this content above the `TESTS` list, and add the three new test function names to `TESTS`. This codebase has no pytest, so there's no `monkeypatch` fixture — `_MiniMonkeypatch` below is a minimal stand-in:

```python
from unittest.mock import MagicMock
import tools_vehicle


class _FakeCache:
    """In-memory stand-in for redis_cache.get_cache/set_cache, so these
    tests don't depend on a live Redis instance being reachable."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl=None):
        self.store[key] = value


class _MiniMonkeypatch:
    """Minimal setattr-and-restore helper (this codebase has no pytest,
    so there's no monkeypatch fixture)."""

    def __init__(self):
        self._restore = []

    def setattr(self, obj, name, value):
        self._restore.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, value in reversed(self._restore):
            setattr(obj, name, value)


def test_get_vehicles_filters_sorts_and_caches():
    monkeypatch = _MiniMonkeypatch()
    try:
        fake_cache = _FakeCache()
        monkeypatch.setattr(tools_vehicle, "get_cache", fake_cache.get)
        monkeypatch.setattr(tools_vehicle, "set_cache", fake_cache.set)

        fake_client = MagicMock()
        fake_client.vehicles.return_value = {
            "result": {
                "data": [
                    {"id": 1, "name": "Truck A", "vehicle_status": "moving", "speed": "80", "driver_name": "Omar"},
                    {"id": 2, "name": "Van B", "vehicle_status": "idle", "speed": "0", "driver_name": "Sara"},
                    {"id": 3, "name": "Truck C", "vehicle_status": "moving", "speed": "40", "driver_name": "Ali"},
                ]
            }
        }
        monkeypatch.setattr(tools_vehicle, "_client", fake_client)

        result = tools_vehicle.get_vehicles.invoke({
            "status": "moving",
            "sort_by": "speed",
            "sort_direction": "desc",
            "limit": 5,
        })

        assert "2 matched" in result, result
        assert result.index("Truck A") < result.index("Truck C"), result
        assert "Van B" not in result, result

        # Second call should hit the fake cache, not the client again.
        fake_client.vehicles.reset_mock()
        tools_vehicle.get_vehicles.invoke({"status": "moving"})
        fake_client.vehicles.assert_not_called()
    finally:
        monkeypatch.undo()


def test_get_vehicles_reports_pitstrack_error():
    monkeypatch = _MiniMonkeypatch()
    try:
        fake_client = MagicMock()
        fake_client.vehicles.side_effect = tools_vehicle.PitstrackError(
            "Pitstrack unavailable: boom"
        )
        monkeypatch.setattr(tools_vehicle, "_client", fake_client)
        monkeypatch.setattr(tools_vehicle, "get_cache", lambda key: None)

        result = tools_vehicle.get_vehicles.invoke({})

        assert "Error" in result, result
        assert "unavailable" in result, result
    finally:
        monkeypatch.undo()


def test_get_working_hours_requires_client_call_with_right_args():
    monkeypatch = _MiniMonkeypatch()
    try:
        fake_cache = _FakeCache()
        monkeypatch.setattr(tools_vehicle, "get_cache", fake_cache.get)
        monkeypatch.setattr(tools_vehicle, "set_cache", fake_cache.set)

        fake_client = MagicMock()
        fake_client.working_hours.return_value = {
            "result": {"data": [{"date": "2026-01-01", "hours": 8}], "total": {"hours": 8}}
        }
        monkeypatch.setattr(tools_vehicle, "_client", fake_client)

        result = tools_vehicle.get_working_hours.invoke({
            "vehicle_id": 42,
            "start_date": "2026-01-01",
            "end_date": "2026-01-01",
        })

        fake_client.working_hours.assert_called_once_with(
            vehicle_id=42,
            start_date="2026-01-01",
            end_date="2026-01-01",
            unit_id=None,
        )
        assert "42" in result, result
        assert "Summary" in result, result
    finally:
        monkeypatch.undo()
```

Add all three new test functions to the `TESTS` list.

- [ ] **Step 2: Run test to verify it fails**

```bash
python test_tools_vehicle.py
```

Expected: `AttributeError: module 'tools_vehicle' has no attribute 'get_vehicles'` (or similar) for the new tests.

- [ ] **Step 3: Write the implementation**

Append to `Testing_AI_Agent_Python/vehicle_agent/tools_vehicle.py`:

```python
import secrets

from langchain.tools import tool

try:
    from .pitstrack_client import PitstrackClient, PitstrackError
except ImportError:
    from pitstrack_client import PitstrackClient, PitstrackError

try:
    from .redis_cache import get_cache, set_cache
except ImportError:
    from redis_cache import get_cache, set_cache


# =========================================================
# Shared client
# =========================================================
#
# No per-user auth needed (unlike LibraryAPIClient) - Pitstrack uses a
# single shared token/account from the environment, so this can be
# constructed directly at import time.

_client = PitstrackClient()


# =========================================================
# Cache keys
# =========================================================

VEHICLES_KEY = "vehicle:list"
VEHICLES_CACHE_TTL = 60  # fleet position/status goes stale fast

WORKING_HOURS_CACHE_TTL = 300  # historical ranges rarely change


def _working_hours_cache_key(
    vehicle_id: int,
    start_date: str,
    end_date: str,
    unit_id: int | None,
) -> str:
    return f"vehicle:working_hours:{vehicle_id}:{start_date}:{end_date}:{unit_id}"


def _fetch_vehicles() -> list[dict]:

    cached = get_cache(VEHICLES_KEY)

    if cached is not None:
        return cached

    response = _client.vehicles()
    rows = _extract(response)

    set_cache(VEHICLES_KEY, rows, ttl=VEHICLES_CACHE_TTL)

    return rows


# =========================================================
# get_vehicles
# =========================================================

@tool
def get_vehicles(
    status: str | None = None,
    driver_name: str | None = None,
    min_speed: float | None = None,
    max_speed: float | None = None,
    sort_by: str | None = None,
    sort_direction: str = "asc",
    limit: int = 20,
    selection: str = "first",
) -> str:
    """
    List current Pitstrack fleet vehicles (cars, trucks, vans, trackers).

    Use this for any question about how many vehicles exist, their
    status, driver, speed, odometer, or a filtered/sorted/sampled list
    of them. The reported count is always the number of vehicles that
    matched the filters, before limit/selection narrows what's shown.

    Args:
        status: Exact vehicle_status to filter by (e.g. "moving", "idle", "offline").
        driver_name: Substring match against driver_name.
        min_speed: Only vehicles with speed >= this value.
        max_speed: Only vehicles with speed <= this value.
        sort_by: Field to sort by (e.g. "speed", "odometer", "name").
        sort_direction: "asc" or "desc". Use "desc" for fastest/highest/most.
        limit: Maximum vehicles to return (1-50).
        selection: "first" for the top `limit` after sorting, or "random"
            for a random sample of `limit` matching vehicles.
    """

    try:
        rows = _fetch_vehicles()
    except PitstrackError as e:
        return f"Error: {e}"

    filters = []

    if status:
        filters.append({"field": "vehicle_status", "operator": "=", "value": status})

    if driver_name:
        filters.append({"field": "driver_name", "operator": "like", "value": driver_name})

    if min_speed is not None:
        filters.append({"field": "speed", "operator": ">=", "value": min_speed})

    if max_speed is not None:
        filters.append({"field": "speed", "operator": "<=", "value": max_speed})

    matched = _filter_rows(rows, filters)
    matched_count = len(matched)

    sort = None
    if sort_by:
        direction = sort_direction if sort_direction in {"asc", "desc"} else "asc"
        sort = {"field": sort_by, "direction": direction}

    matched = _sort_rows(matched, sort)

    limit = min(max(int(limit or 20), 1), 50)

    if selection == "random":
        shown = secrets.SystemRandom().sample(matched, min(limit, matched_count))
    else:
        shown = matched[:limit]

    if matched_count == 0:
        return "No vehicles matched."

    lines = [f"Vehicles ({matched_count} matched, showing {len(shown)}):"]

    for row in _vehicle_view(shown):
        lines.append(
            f"- {row.get('name', 'Unknown')} "
            f"[{row.get('vehicle_status', 'unknown')}] "
            f"driver={row.get('driver_name', '-')} "
            f"speed={row.get('speed', '-')} "
            f"odometer={row.get('odometer', '-')}"
        )

    return "\n".join(lines)


# =========================================================
# get_working_hours
# =========================================================

@tool
def get_working_hours(
    vehicle_id: int,
    start_date: str,
    end_date: str,
    unit_id: int | None = None,
) -> str:
    """
    Get working-hours/distance data for one vehicle over a date range.

    Use this after identifying a specific vehicle (by id, from
    get_vehicles) when the question needs working hours, distance, or
    a period summary.

    Args:
        vehicle_id: The Pitstrack vehicle id.
        start_date: Start date, YYYY-MM-DD.
        end_date: End date, YYYY-MM-DD.
        unit_id: Optional specific tracking unit id.
    """

    key = _working_hours_cache_key(vehicle_id, start_date, end_date, unit_id)

    cached = get_cache(key)

    if cached is not None:
        rows = cached
    else:
        try:
            response = _client.working_hours(
                vehicle_id=vehicle_id,
                start_date=start_date,
                end_date=end_date,
                unit_id=unit_id,
            )
        except PitstrackError as e:
            return f"Error: {e}"

        rows = _extract(response, include_total=True)

        set_cache(key, rows, ttl=WORKING_HOURS_CACHE_TTL)

    if not rows:
        return f"No working-hours data for vehicle {vehicle_id} in that range."

    lines = [f"Working hours for vehicle {vehicle_id} ({start_date} to {end_date}):"]

    for row in rows:
        if row.get("__summary__"):
            summary = ", ".join(
                f"{k}={v}" for k, v in row.items() if k != "__summary__"
            )
            lines.append(f"- Summary: {summary}")
        else:
            lines.append(f"- {row}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python test_tools_vehicle.py
```

Expected: `16/16 passed`.

- [ ] **Step 5: Commit**

```bash
git add tools_vehicle.py test_tools_vehicle.py
git commit -m "vehicle_agent: add get_vehicles/get_working_hours tools with Redis caching

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Trim router.py

**Files:**
- Modify: `Testing_AI_Agent_Python/vehicle_agent/router.py` (replace entire content)

**Interfaces:**
- Produces: `ToolGroup = Literal["vehicles", "general"]`. Nothing else — `get_direct_tool`, `resolve_history_tool`, `extract_history_target`, `DIRECT_TOOL_GROUP` are all removed (library-specific, no vehicle analogue, per spec's Routing decision).

- [ ] **Step 1: Replace the file**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/router.py`:

```python
"""
Shared routing type for vehicle_agent.

There is no deterministic fast path here (unlike redis_agent2's
get_direct_tool/resolve_history_tool) - Pitstrack queries are
inherently parameterized (filters/sort/date-ranges), not fixed exact
phrases, so every message goes through the AI router.
"""

from typing import Literal

ToolGroup = Literal[
    "vehicles",
    "general",
]
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
python -c "from router import ToolGroup; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add router.py
git commit -m "vehicle_agent: trim router.py to just the ToolGroup type

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Rewrite router_keyword_backup.py for vehicles

**Files:**
- Modify: `Testing_AI_Agent_Python/vehicle_agent/router_keyword_backup.py` (replace entire content)
- Test: `Testing_AI_Agent_Python/vehicle_agent/test_router_keyword_backup.py` (new)

**Interfaces:**
- Produces: `route_request(user_message: str) -> Literal["vehicles", "general"]` — the safety-net fallback `ai_router.classify_route` (Task 8) calls when the LLM's output can't be parsed.

- [ ] **Step 1: Write the failing test**

Create `Testing_AI_Agent_Python/vehicle_agent/test_router_keyword_backup.py`:

```python
"""
Unit tests for the keyword-based fallback router.
"""

from router_keyword_backup import route_request


CASES = [
    ("show all vehicles", "vehicles"),
    ("how many trucks are moving", "vehicles"),
    ("what is the fleet status", "vehicles"),
    ("show working hours for vehicle 12", "vehicles"),
    ("where is the van", "vehicles"),
    ("hello", "general"),
    ("thanks!", "general"),
    ("what can you do?", "general"),
]


def test_keyword_routing():
    for message, expected in CASES:
        actual = route_request(message)
        assert actual == expected, f"{message!r}: expected {expected!r}, got {actual!r}"


TESTS = [test_keyword_routing]


def main():
    passed = 0
    failed = 0

    for test in TESTS:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} passed")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python test_router_keyword_backup.py
```

Expected: `ModuleNotFoundError` (module still has book/member/borrowing keywords, or old content).

- [ ] **Step 3: Write the implementation**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/router_keyword_backup.py`:

```python
"""
Keyword-based route classifier - retained as a safety-net fallback.

ai_router.classify_route() calls into this module only when the LLM
router's output cannot be parsed into "vehicles". Kept so routing
never has a hard failure mode.
"""

from typing import Literal

ToolGroup = Literal[
    "vehicles",
    "general",
]


VEHICLE_KEYWORDS = [
    "vehicle",
    "vehicles",
    "fleet",
    "car",
    "cars",
    "truck",
    "trucks",
    "van",
    "vans",
    "driver",
    "tracker",
    "trackers",
    "odometer",
    "speed",
    "location",
    "working hours",
    "working hour",
    "distance",
    "moving",
    "idle",
    "offline",
]


def route_request(user_message: str) -> ToolGroup:
    """
    Determine whether the request needs live fleet data, using plain
    keyword/substring matching.
    """

    text = user_message.lower().strip()

    if any(keyword in text for keyword in VEHICLE_KEYWORDS):
        return "vehicles"

    return "general"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python test_router_keyword_backup.py
```

Expected: `1/1 passed`.

- [ ] **Step 5: Commit**

```bash
git add router_keyword_backup.py test_router_keyword_backup.py
git commit -m "vehicle_agent: rewrite keyword fallback router for the vehicles domain

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Adapt ai_router.py and prompts/router.md

**Files:**
- Modify: `Testing_AI_Agent_Python/vehicle_agent/ai_router.py`
- Modify: `Testing_AI_Agent_Python/vehicle_agent/prompts/router.md` (replace entire content)
- Rewrite: `Testing_AI_Agent_Python/vehicle_agent/test_ai_router.py` (replace entire content — live-Ollama test, matching the existing structure but vehicle phrasings)

**Interfaces:**
- Consumes: `router_keyword_backup.route_request` (Task 7).
- Produces: `classify_route(user_message: str) -> Literal["vehicles", "general"]`. Task 10 (`routed_agent.py`) calls this exactly as `redis_agent2` calls its own.

- [ ] **Step 1: Rewrite prompts/router.md**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/prompts/router.md`:

```
You are the routing controller for a fleet-tracking assistant.

Decide whether the user's request needs live Pitstrack fleet data.
Reply with ONLY one word - no punctuation, no explanation, no other
text.

vehicles: any question about the fleet's vehicles, trucks, cars, vans,
trackers, drivers, status, speed, odometer, location, or working
hours/distance over a date range - including counts, lists, filters,
comparisons, or a specific vehicle's details.

If the request is NOT about live fleet data (a greeting, general
conversation, or something unrelated), reply "vehicles" only when it
genuinely needs fleet data - otherwise do not reply "vehicles" at all;
just answer that you are unsure, since unparseable output correctly
falls back to a safe default.

Reply with exactly one word: vehicles

Examples:
"how many trucks do we have" -> vehicles
"show me the fastest vehicle" -> vehicles
"where is truck 12 right now" -> vehicles
"working hours for vehicle 7 last week" -> vehicles
"hello" -> (do not answer "vehicles" - this is not a fleet question)
```

- [ ] **Step 2: Modify ai_router.py**

In `Testing_AI_Agent_Python/vehicle_agent/ai_router.py`, make these exact changes:

Replace the `AiRoute`/`AI_ROUTES` block:

```python
AiRoute = Literal[
    "vehicles",
]

AI_ROUTES: set[AiRoute] = {
    "vehicles",
}
```

Replace `AI_ROUTE_SYNONYMS`:

```python
AI_ROUTE_SYNONYMS: dict[str, AiRoute] = {
    "vehicle": "vehicles",
    "fleet": "vehicles",
    "car": "vehicles",
    "cars": "vehicles",
    "truck": "vehicles",
    "trucks": "vehicles",
    "van": "vehicles",
    "vans": "vehicles",
    "tracker": "vehicles",
    "trackers": "vehicles",
}
```

Leave every other function (`_get_router_model`, `_parse_route`, `classify_route`, the `PROMPTS_DIR`/`_load_prompt` loader) exactly as-is — they're domain-agnostic and already read `router.md` at import time.

- [ ] **Step 3: Rewrite test_ai_router.py**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/test_ai_router.py`:

```python
"""
Live test for the AI router - hits Ollama for real, same as
redis_agent2/test_ai_router.py. Requires Ollama running locally.
"""

from ai_router import classify_route


TEST_CASES = [
    ("how many trucks do we have", "vehicles"),
    ("show me the fastest vehicle", "vehicles"),
    ("where is truck 12 right now", "vehicles"),
    ("working hours for vehicle 7 last week", "vehicles"),
    ("which vehicles are idle", "vehicles"),
    ("who is driving van 3", "vehicles"),
]


def main():
    print("=== AI Router Test (vehicle_agent) ===\n")

    passed = 0
    failed = 0

    for message, expected in TEST_CASES:
        actual = classify_route(message)
        ok = actual == expected

        status = "PASS" if ok else "FAIL"

        if ok:
            passed += 1
        else:
            failed += 1

        print(
            f"[{status}] {message!r}\n"
            f"       expected={expected!r} actual={actual!r}"
        )

    total = passed + failed
    print(f"\n=== {passed}/{total} passed ({failed} failed) ===")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the live test**

```bash
python test_ai_router.py
```

Expected: all 6 cases print `actual='vehicles'` (Ollama must be running — confirmed reachable earlier in this project). A failure here means the router prompt needs another iteration, same as happened with `redis_agent2` earlier — if any case is wrong, inspect the raw model output the same way (temporarily print it inside `classify_route`) before adjusting `router.md`'s wording, rather than guessing.

- [ ] **Step 5: Commit**

```bash
git add ai_router.py prompts/router.md test_ai_router.py
git commit -m "vehicle_agent: adapt ai_router.py and router.md for the vehicles/general split

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Vehicle prompts (base_agent.md, vehicles_agent.md, general_agent.md)

**Files:**
- Modify: `Testing_AI_Agent_Python/vehicle_agent/prompts/base_agent.md` (replace entire content)
- Create: `Testing_AI_Agent_Python/vehicle_agent/prompts/vehicles_agent.md`
- Verify: `Testing_AI_Agent_Python/vehicle_agent/prompts/general_agent.md` (check content, likely needs no change)

**Interfaces:**
- Produces: prompt text files. Task 10 (`routed_agent.py`) loads them via the same `_load_prompt`/`GROUP_PROMPTS` pattern `redis_agent2` already uses.

- [ ] **Step 1: Rewrite base_agent.md**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/prompts/base_agent.md`:

```
You are a concise fleet-tracking assistant for a Pitstrack-connected
vehicle fleet.

GENERAL RULES:
- Use tools whenever live fleet data is required.
- Never invent vehicle data - status, speed, location, driver, or
  working hours must come from a tool result, not a guess.
- Report tool errors directly.
- Be concise.
- Format lists compactly, one item per line.

CONVERSATION MEMORY:
- Previous messages are provided as part of the current conversation.
- Use previous messages to understand references such as "that
  vehicle", "the second one", "the one you just mentioned", etc.
- Do not claim that you cannot remember something when it is present
  in the conversation history.
- Conversation history may contain an earlier live-data answer. Use
  it only to understand follow-up references - never treat its values
  as current facts. Call the relevant tool again before answering a
  follow-up that depends on current data.
```

- [ ] **Step 2: Create vehicles_agent.md**

Create `Testing_AI_Agent_Python/vehicle_agent/prompts/vehicles_agent.md`:

```
You are handling a fleet/vehicle request.

Use get_vehicles for any question about vehicle count, status,
driver, speed, odometer, or a filtered/sorted/sampled list of the
fleet.

Use get_working_hours after identifying a specific vehicle id when
the question needs working hours, distance, or a period summary over
a date range.

Do not invent a vehicle id - resolve it via get_vehicles first if the
user only gave a name.

Use conversation history when the user refers to a vehicle mentioned
previously.
```

- [ ] **Step 3: Verify general_agent.md needs no change**

```bash
cat "Testing_AI_Agent_Python/vehicle_agent/prompts/general_agent.md"
```

Confirm it reads (already domain-agnostic, ported unchanged from `redis_agent2`):

```
The request does not clearly belong to a specific tool group.

Answer directly if possible.

If library data is required, use the available tools.

Use conversation history to answer questions about information
the user provided earlier.
```

The phrase "library data" is a leftover — fix it in place since it's factually wrong for this agent:

- [ ] **Step 4: Fix the leftover "library" wording in general_agent.md**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/prompts/general_agent.md`:

```
The request does not clearly belong to a specific tool group.

Answer directly if possible.

If live fleet data is required, use the available tools.

Use conversation history to answer questions about information
the user provided earlier.
```

- [ ] **Step 5: Verify all four files load without error**

```bash
python -c "
from pathlib import Path
d = Path('prompts')
for name in ['base_agent.md', 'vehicles_agent.md', 'general_agent.md', 'router.md']:
    text = (d / name).read_text(encoding='utf-8').strip()
    print(name, '->', len(text), 'chars, first line:', text.splitlines()[0])
"
```

Expected: all four print a nonzero length and a sensible first line, no errors.

- [ ] **Step 6: Commit**

```bash
git add prompts/
git commit -m "vehicle_agent: rewrite prompts for the fleet-tracking domain

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Rewrite routed_agent.py

**Files:**
- Modify: `Testing_AI_Agent_Python/vehicle_agent/routed_agent.py` (replace entire content)

**Interfaces:**
- Consumes: `classify_route` (Task 8), `get_vehicles`/`get_working_hours` (Task 5), `GROUP_PROMPTS` sourced from Task 9's files, `ConversationMemory`/`LibraryAPIClient` (unchanged).
- Produces: `invoke_routed_agent(user_message: str, conversation_id: int | None = None) -> tuple[dict, str]` — same return contract as `redis_agent2`, so `streamlit_app_routed.py` (Task 11) needs no logic changes, only label changes.

- [ ] **Step 1: Replace the file**

Replace the full content of `Testing_AI_Agent_Python/vehicle_agent/routed_agent.py`:

```python
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

MEMORY_WINDOW = 10

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
    from .ai_router import classify_route
except ImportError:
    from ai_router import classify_route


try:
    from .redis_cache import get_cache, set_cache
except ImportError:
    from redis_cache import get_cache, set_cache


try:
    from .tools_vehicle import get_vehicles, get_working_hours
except ImportError:
    from tools_vehicle import get_vehicles, get_working_hours


# =========================================================
# LibrarySystem identity (per-user login, conversation memory)
# =========================================================
#
# Pitstrack itself has no per-user login - it's a single shared
# account (see pitstrack_client.py). This client is only for the
# LibrarySystem user's identity and MySQL-backed conversation history,
# exactly as in redis_agent2.

api = LibraryAPIClient(interactive=True)


# =========================================================
# Tool groups
# =========================================================

VEHICLE_TOOLS = [
    get_vehicles,
    get_working_hours,
]


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
    # when its thinking step runs - reasoning=False makes it print
    # the tool call as plain JSON text instead, which the agent can't
    # execute. See redis_agent2/routed_agent.py for the full story.
    reasoning=True,
    keep_alive="30m",
    num_predict=150,
)


# =========================================================
# System prompts
# =========================================================
#
# Loaded once at import time from prompts/*.md - not re-read per
# request.

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


BASE_PROMPT = _load_prompt("base_agent.md")

GROUP_PROMPTS = {
    group: BASE_PROMPT + "\n\n" + _load_prompt(f"{group}_agent.md")
    for group in ("vehicles", "general")
}


# =========================================================
# Create one agent per tool group
# =========================================================

agents = {
    "vehicles": create_agent(
        model=model,
        tools=VEHICLE_TOOLS,
        system_prompt=GROUP_PROMPTS["vehicles"],
    ),
    "general": create_agent(
        model=model,
        tools=[],
        system_prompt=GROUP_PROMPTS["general"],
    ),
}


# =========================================================
# Response cache
# =========================================================
#
# Caches the final text answer for the "vehicles" group, scoped per
# authenticated LibrarySystem user. Never used for "general" (chit-chat
# leans on conversation context the most). No invalidation-on-write is
# needed - this domain is read-only, so TTL alone keeps it correct.

RESPONSE_CACHEABLE_GROUPS = {"vehicles"}
RESPONSE_CACHE_TTL = 300


def _response_cache_key(group: str, user_message: str) -> str:

    token = getattr(api, "token", "anonymous")
    normalized = user_message.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    return f"vehicle:ai_response:{group}:{token}:{digest}"


# =========================================================
# Memory helpers
# =========================================================

def _load_conversation_messages(
    conversation_id: int | None,
) -> list[dict[str, Any]]:

    if conversation_id is None:
        return []

    memory = ConversationMemory(
        api_client=api,
        conversation_id=conversation_id,
    )

    messages = memory.get_recent_messages(limit=MEMORY_WINDOW)

    print(f"[MEMORY] Loaded {len(messages)} persistent messages.")

    return messages


def _save_user_message(conversation_id: int | None, content: str) -> None:

    if conversation_id is None:
        return

    memory = ConversationMemory(api_client=api, conversation_id=conversation_id)
    memory.save_user_message(content)

    print("[MEMORY] User message saved.")


def _save_assistant_message(conversation_id: int | None, content: str) -> None:

    if conversation_id is None:
        return

    memory = ConversationMemory(api_client=api, conversation_id=conversation_id)
    memory.save_assistant_message(content)

    print("[MEMORY] Assistant message saved.")


def _convert_history_to_langchain_messages(
    history: list[dict[str, Any]],
) -> list[Any]:

    messages: list[Any] = []

    for message in history:
        role = message.get("role")
        content = message.get("content")

        if not role or content is None:
            continue

        messages.append({"role": role, "content": content})

    return messages


def _extract_final_assistant_response(result: Any) -> str:

    messages = result.get("messages", [])

    for message in reversed(messages):
        content = getattr(message, "content", None)

        if content is None:
            continue

        if isinstance(content, str):
            if content.strip():
                return content.strip()
        else:
            try:
                return json.dumps(content, ensure_ascii=False)
            except TypeError:
                return str(content)

    return "No response returned."


# =========================================================
# Routed invocation
# =========================================================

def invoke_routed_agent(
    user_message: str,
    conversation_id: int | None = None,
):
    """
    Classify the request into "vehicles" or "general" and send it to
    that group's LangChain agent.

    Persistent conversation memory (Python -> Laravel API -> MySQL)
    works exactly as in redis_agent2 - only the tool domain changed.

    There is no deterministic direct-tool fast path here (Pitstrack
    queries are inherently parameterized, unlike "show all books"), so
    every request is classified.

    Returns:
        (result, group) - same shape as redis_agent2's
        invoke_routed_agent, so streamlit_app_routed.py needs no
        logic changes.
    """

    # =====================================================
    # Step 0: Load persistent conversation history
    # =====================================================

    persistent_history = _load_conversation_messages(conversation_id)
    langchain_history = _convert_history_to_langchain_messages(persistent_history)

    # =====================================================
    # Step 1: Classify the request
    # =====================================================

    group = classify_route(user_message)

    print()
    print("=" * 60)
    print(f"[ROUTER] Request           : {user_message}")
    print(f"[ROUTER] Group             : {group}")
    print(f"[ROUTER] Persistent memory : {len(langchain_history)} messages")
    print("=" * 60)

    _save_user_message(conversation_id, user_message)

    # =====================================================
    # Step 2: Response cache - skip the LLM call on a hit
    # =====================================================

    response_cache_key = None

    if group in RESPONSE_CACHEABLE_GROUPS:

        response_cache_key = _response_cache_key(group, user_message)
        cached_response = get_cache(response_cache_key)

        if cached_response is not None:

            print(f"[RESPONSE_CACHE] HIT for group={group}")

            _save_assistant_message(conversation_id, cached_response)

            return {
                "messages": [],
                "direct": True,
                "tool": None,
                "response": cached_response,
                "cached": True,
            }, group

        print(f"[RESPONSE_CACHE] MISS for group={group}")

    # =====================================================
    # Step 3: LLM agent execution
    # =====================================================

    print(f"[ROUTER] Sending request to {group} LLM agent")

    selected_agent = agents[group]

    messages_for_agent: list[Any] = langchain_history + [
        {"role": "user", "content": user_message}
    ]

    print(f"[MEMORY] Sending {len(messages_for_agent)} messages to {group} agent.")

    result = selected_agent.invoke({"messages": messages_for_agent})

    assistant_response = _extract_final_assistant_response(result)

    _save_assistant_message(conversation_id, assistant_response)

    if response_cache_key is not None:
        set_cache(response_cache_key, assistant_response, ttl=RESPONSE_CACHE_TTL)

    return result, group
```

- [ ] **Step 2: Verify the module-independent logic (prompt loading, agent group keys) without triggering the interactive Laravel login**

`routed_agent.py` constructs `LibraryAPIClient(interactive=True)` at import time, which blocks on `input()` for email/password in a real terminal — this is a pre-existing trait shared with `redis_agent2`, out of scope to change here. Verify the parts that don't need it by extracting them into an isolated check:

```bash
python -c "
from pathlib import Path

PROMPTS_DIR = Path('prompts')

def _load_prompt(name):
    return (PROMPTS_DIR / name).read_text(encoding='utf-8').strip()

BASE_PROMPT = _load_prompt('base_agent.md')
GROUP_PROMPTS = {
    group: BASE_PROMPT + '\n\n' + _load_prompt(f'{group}_agent.md')
    for group in ('vehicles', 'general')
}

assert set(GROUP_PROMPTS.keys()) == {'vehicles', 'general'}
assert 'get_vehicles' in GROUP_PROMPTS['vehicles'] or 'get_vehicles' not in GROUP_PROMPTS['vehicles']  # sanity: no crash
print('GROUP_PROMPTS keys:', list(GROUP_PROMPTS.keys()))
print('vehicles prompt length:', len(GROUP_PROMPTS['vehicles']))
print('general prompt length:', len(GROUP_PROMPTS['general']))
print('OK')
"
```

Expected: `OK` with sensible non-zero lengths — confirms Task 9's prompt files combine correctly under `routed_agent.py`'s exact loading logic.

- [ ] **Step 3: Byte-compile the full file to catch syntax errors**

```bash
python -m py_compile routed_agent.py
```

Expected: no output (success).

- [ ] **Step 4: Manual end-to-end check (requires the user to run it interactively)**

This step cannot be automated in this environment (needs a real terminal for the `LibraryAPIClient` login prompt, plus Laravel and Ollama running). Tell the user to run:

```bash
python -c "from routed_agent import invoke_routed_agent; print(invoke_routed_agent('hello', None))"
```

from `Testing_AI_Agent_Python/vehicle_agent/`, log in when prompted, and confirm it returns a `(dict, "general")` tuple with a real greeting — this is the first true end-to-end proof the wiring works, and should happen before or during Task 11's Streamlit check.

- [ ] **Step 5: Commit**

```bash
git add routed_agent.py
git commit -m "vehicle_agent: rewrite routed_agent.py for the vehicles/general domain

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 11: Relabel streamlit_app_routed.py

**Files:**
- Modify: `Testing_AI_Agent_Python/vehicle_agent/streamlit_app_routed.py`

**Interfaces:**
- Consumes: `invoke_routed_agent` (Task 10) — same call signature, no logic changes needed here.

- [ ] **Step 1: Update the title, caption, and placeholder text**

In `Testing_AI_Agent_Python/vehicle_agent/streamlit_app_routed.py`, make these exact text replacements (everything else — session state, chat loop, response extraction, error handling — stays unchanged):

```python
st.set_page_config(
    page_title="Fleet Assistant - Routed",
    page_icon="🚚",
    layout="centered",
)
```

```python
st.title("🚚 Fleet Assistant")
st.caption("LangChain + Ollama + Redis + Pitstrack")
```

```python
conversation_id = memory.create(
    title="Fleet Assistant Conversation"
)
```

```python
user_message = st.chat_input(
    "Ask about your fleet - vehicles, status, drivers, or working hours..."
)
```

- [ ] **Step 2: Verify no leftover library wording remains**

```bash
grep -in "book\|member\|borrow\|library" streamlit_app_routed.py
```

Expected: no output. If anything matches, fix that specific line before continuing.

- [ ] **Step 3: Byte-compile to catch syntax errors**

```bash
python -m py_compile streamlit_app_routed.py
```

Expected: no output (success).

- [ ] **Step 4: Commit**

```bash
git add streamlit_app_routed.py
git commit -m "vehicle_agent: relabel Streamlit app for fleet tracking

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 12: Final verification pass

**Files:** none new — verification only.

**Interfaces:** N/A.

- [ ] **Step 1: Run every test file written in this plan**

```bash
cd "Testing_AI_Agent_Python/vehicle_agent"
python test_pitstrack_client_unit.py
python test_tools_vehicle.py
python test_router_keyword_backup.py
python test_ai_router.py
```

Expected: all four print `N/N passed` with no failures (the `test_ai_router.py` run needs Ollama running, same as Task 8).

- [ ] **Step 2: Confirm no dangling library-domain tool references outside the deferred benchmark files**

```bash
grep -rl "search_books\|borrow_book\|return_book\|list_members\|my_profile\|LibraryAPIClient()" *.py | grep -v "^routed_agent.py$"
```

Expected: only `benchmark_routing.py` and `benchmark_routing_v2.py` (explicitly deferred per the spec — do not touch them in this plan). `routed_agent.py` legitimately still constructs `LibraryAPIClient` for identity/memory, which is why it's excluded from this check.

- [ ] **Step 3: Byte-compile every Python file in the directory**

```bash
python -m py_compile *.py
```

Expected: no output (success) — confirms nothing is left syntactically broken, including the deferred benchmark files (a compile check doesn't run imports, so their broken *imports* won't surface here — only actual syntax errors would).

- [ ] **Step 4: Final commit (only if any of the above steps required a fix)**

```bash
git add -A
git commit -m "vehicle_agent: final verification pass

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

If no fixes were needed, skip this commit — there's nothing to commit.

- [ ] **Step 5: Note for follow-up (not part of this plan)**

`tools_vehicle.py`'s `DEFAULT_VEHICLE_FIELDS` and `get_vehicles`'s output
line format were written against the reference project's assumed field
names (`vehicle_status`, `driver_name`, `odometer`, `speed`,
`device_number`, ...) — this was one of the spec's explicitly flagged
open questions ("exact list of vehicle fields... may need adjusting
once real Pitstrack data is inspected"). Once the user has verified a
real token in Postman/`test_pitstrack_client.py` (Task 3) and can see
actual field names in a live response, compare them against
`DEFAULT_VEHICLE_FIELDS` and adjust if they differ — this is expected
follow-up, not a defect in this plan.
