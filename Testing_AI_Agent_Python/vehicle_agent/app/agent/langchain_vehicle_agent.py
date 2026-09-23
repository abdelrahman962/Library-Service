"""LangChain/LangGraph tool-calling agent for fleet conversation and data.

This is a parallel implementation of :mod:`app.agent.vehicle_agent`, built
on LangChain's own agent loop (`langchain.agents.create_agent`, which runs
on LangGraph) and LangGraph's own persistent memory (a SQLite checkpointer)
instead of the hand-rolled `OllamaClient`/`ConversationMemory` there. It
exists purely for side-by-side comparison; it does not modify, import
runtime behavior from, or get imported by the original agent -- the two
only share the system prompt text and the existing, already-safe data
tools in `app.agent.tools.AgentTools`.

There is still deliberately no intent classifier and no keyword matching
here. Each tool is described to the model through its type-annotated
signature and docstring, exactly like the original JSON tool schemas, and
the model alone decides -- semantically -- whether and which tool to call.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langchain.agents import create_agent
from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel, Field

from app.agent.tools import AgentTools
from app.agent.vehicle_agent import SYSTEM_PROMPT
from app.config.settings import settings
from app.services.pitstrack import PitstrackError


# =====================================================================
# Argument schemas
#
# These describe *capabilities*, not question patterns -- the same
# philosophy as the JSON tool schemas in app/agent/tools.py. The model
# reads the field descriptions and decides semantically; nothing here
# inspects the user's wording.
# =====================================================================

class FilterArg(BaseModel):
    field: str = Field(description="Column name to filter on.")
    operator: str = Field(
        description=(
            "One of =, !=, >, >=, <, <=, like, not like, in, not in, "
            "is null, is not null."
        ),
    )
    value: Any = Field(
        default=None,
        description="Comparison value. Omit for is null / is not null.",
    )


class SortArg(BaseModel):
    field: str = Field(description="Field to order by.")
    direction: Literal["asc", "desc"] = Field(
        default="asc",
        description="desc = greatest value first; asc = smallest value first.",
    )


# =====================================================================
# Per-invocation context (the signed-in user). Injected into tools by
# LangGraph via `ToolRuntime` -- never part of the schema the model sees.
# =====================================================================

class AgentContext(TypedDict):
    user_id: int


# =====================================================================
# Tool execution: reuses the existing, already-safe AgentTools methods.
# No business logic (filtering, sorting, caching) is reimplemented here.
# =====================================================================

MAX_RESULT_CHARACTERS = 12_000


def _run_tool(shared: AgentTools, name: str, arguments: dict[str, Any], user_id: int) -> Any:
    """Execute a data tool and translate failures into a model-safe result.

    Mirrors the error mapping in `VehicleAgent._execute_tool`: the model
    receives a plain, honest failure reason instead of a raw traceback or
    a crashed tool call.
    """
    try:
        result = shared.execute(name, arguments, user_id)
    except PitstrackError:
        return {"ok": False, "error": "The vehicle data source is currently unavailable."}
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": f"Invalid tool arguments: {exc}"}
    except Exception:
        return {"ok": False, "error": "The requested data operation could not be completed."}

    encoded = str(result)
    if len(encoded) > MAX_RESULT_CHARACTERS:
        return {
            "ok": False,
            "error": (
                "The result is too large for one response. Use narrower filters, "
                "selected fields, or a smaller limit."
            ),
        }
    return {"ok": True, "data": result}


def _dump(value: BaseModel | None) -> dict[str, Any] | None:
    return value.model_dump(exclude_none=True) if value is not None else None


def _dump_list(values: list[BaseModel] | None) -> list[dict[str, Any]]:
    return [item.model_dump(exclude_none=True) for item in values or []]


def build_tools(shared: AgentTools) -> list:
    """Build the LangChain tools bound to one shared `AgentTools` instance."""

    @tool
    def get_vehicles(
        runtime: ToolRuntime[AgentContext],
        filters: Annotated[
            list[FilterArg] | None,
            Field(description="Conditions to filter vehicle records by."),
        ] = None,
        sort: SortArg | None = None,
        limit: Annotated[
            int | None,
            Field(ge=1, le=50, description="Maximum rows to return."),
        ] = None,
        selection: Annotated[
            Literal["first", "random"],
            Field(description="Use random for a random sample; first otherwise."),
        ] = "first",
        fields: Annotated[
            list[str] | None,
            Field(description="Optional vehicle fields needed in the answer."),
        ] = None,
    ) -> Any:
        """Read current Pitstrack vehicle records.

        Use only for factual, current vehicle/fleet data: cars, trucks,
        vans, and tracker-equipped devices. Common fields include id,
        name, odometer, speed, vehicle_status, driver_name, device_number,
        longitude, and latitude. Every result includes `matched_count`,
        the exact number of all matching records before limiting or
        sampling -- use it for any total/count question about the fleet.
        """
        arguments = {
            "filters": _dump_list(filters),
            "sort": _dump(sort),
            "limit": limit,
            "selection": selection,
            "fields": fields,
        }
        return _run_tool(shared, "get_vehicles", arguments, runtime.context["user_id"])

    @tool
    def get_working_hours(
        vehicle_id: Annotated[int, Field(description="The Pitstrack vehicle id.")],
        start_date: Annotated[str, Field(description="Start date, YYYY-MM-DD.")],
        end_date: Annotated[str, Field(description="End date, YYYY-MM-DD.")],
        runtime: ToolRuntime[AgentContext],
        page: int = 1,
        unit_id: int | None = None,
    ) -> Any:
        """Read Pitstrack working-hours data for one vehicle over a date range.

        Use after obtaining a vehicle id when the answer needs working
        hours, distance, or a period summary for that vehicle.
        """
        arguments = {
            "vehicle_id": vehicle_id,
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "unit_id": unit_id,
        }
        return _run_tool(shared, "get_working_hours", arguments, runtime.context["user_id"])

    return [get_vehicles, get_working_hours]


class LangchainVehicleAgent:
    """Runs the LangChain/LangGraph model-tool loop for one chat turn.

    Memory is LangGraph's own: a `SqliteSaver` checkpointer keyed by
    `thread_id=str(user_id)`, persisted to a local SQLite file -- durable
    across restarts, and written incrementally rather than by rewriting a
    whole JSON file on every message.
    """

    def __init__(
        self,
        *,
        tools: AgentTools | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        self.tools = tools or AgentTools()

        resolved_db_path = (
            Path(db_path)
            if db_path
            else Path(settings.agent_memory_file).parent / "langchain_memory.sqlite"
        )
        resolved_db_path.parent.mkdir(parents=True, exist_ok=True)

        # check_same_thread=False: FastAPI/uvicorn serve sync endpoints from
        # a thread pool. The lock below serializes access to this one
        # connection, since sqlite3 connections are not safe for concurrent
        # writers even with that flag.
        self._conn = sqlite3.connect(str(resolved_db_path), check_same_thread=False)
        self._checkpointer = SqliteSaver(self._conn)
        self._invoke_lock = threading.Lock()

        model = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            num_predict=settings.ollama_num_predict,
            num_ctx=settings.ollama_num_ctx,
            keep_alive=settings.ollama_keep_alive,
            # Equivalent to the original agent's "think": False -- reason
            # internally on supported models, never retain/reveal it.
            reasoning=False,
            client_kwargs={"timeout": settings.ollama_timeout},
        )

        self._graph = create_agent(
            model=model,
            tools=build_tools(self.tools),
            system_prompt=SYSTEM_PROMPT,
            checkpointer=self._checkpointer,
            context_schema=AgentContext,
        )

    def chat(self, message: str, user_id: int) -> dict[str, Any]:
        started = time.perf_counter()
        text = str(message).strip()
        if not text:
            return self._result("أرسل سؤالك أو رسالتك وسأساعدك.", started, tools_used=[])

        config: RunnableConfig = {"configurable": {"thread_id": str(user_id)}}

        with self._invoke_lock:
            try:
                previous_state = self._graph.get_state(config)
                previous_count = (
                    len(previous_state.values.get("messages", []))
                    if previous_state.values
                    else 0
                )

                result = self._graph.invoke(
                    {"messages": [HumanMessage(content=text)]},
                    config=config,
                    context={"user_id": user_id},
                )
            except Exception as exc:
                return self._result(
                    "تعذر إكمال الطلب حاليًا. حاول مرة ثانية بعد قليل.",
                    started,
                    tools_used=[],
                    failures=[str(exc)],
                )

        new_messages = result["messages"][previous_count:]
        tools_used = [msg.name for msg in new_messages if isinstance(msg, ToolMessage) and msg.name]
        failures = [
            str(msg.content)
            for msg in new_messages
            if isinstance(msg, ToolMessage) and self._tool_message_failed(msg)
        ]

        final = result["messages"][-1] if result["messages"] else None
        answer = str(final.content or "").strip() if isinstance(final, AIMessage) else ""

        return self._result(
            answer or "ما قدرت أوصل لإجابة موثوقة ضمن هذه المحاولة. جرّب صياغة الطلب بتفصيل أكثر.",
            started,
            tools_used=tools_used,
            failures=failures,
        )

    @staticmethod
    def _tool_message_failed(message: ToolMessage) -> bool:
        """A tool call can fail two ways: the framework marks it an error
        (bad/invalid arguments), or the tool itself ran fine but reports a
        data-layer failure as `{"ok": false, ...}` (see `_run_tool`) so the
        model gets an honest, in-context reason instead of a crash. Both
        should count as a failure in the returned metadata."""
        if getattr(message, "status", None) == "error":
            return True
        if not isinstance(message.content, str):
            return False
        try:
            payload = json.loads(message.content)
        except ValueError:
            return False
        return isinstance(payload, dict) and payload.get("ok") is False

    @staticmethod
    def _result(
        answer: str,
        started: float,
        *,
        tools_used: list[str],
        failures: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "answer": answer,
            "meta": {
                "mode": "data" if tools_used else "conversation",
                "model": settings.ollama_model,
                "framework": "langchain",
                "tools_used": list(dict.fromkeys(tools_used)),
                "elapsed_ms": round((time.perf_counter() - started) * 1_000, 2),
                "tool_failures": len(failures or []),
            },
        }


langchain_agent = LangchainVehicleAgent()
