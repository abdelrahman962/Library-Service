"""Manual test harness for the LangChain/LangGraph vehicle agent.

Run from the vehicle_agent directory (needs the `app` package on the path):

    streamlit run streamlit_app.py

This talks to `app.agent.langchain_vehicle_agent.langchain_agent` directly
in-process -- no FastAPI/HTTP hop -- so it also works without the service
running, as long as Ollama (and, for data questions, Pitstrack) are
reachable. It exists purely to exercise and time the LangChain agent; it
does not touch the original agent in app/agent/vehicle_agent.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import streamlit as st

from app.agent.langchain_vehicle_agent import langchain_agent
from app.config.settings import settings


@dataclass
class Turn:
    query: str
    answer: str
    elapsed_ms: float
    mode: str
    tools_used: list[str] = field(default_factory=list)
    tool_failures: int = 0


st.set_page_config(page_title="Fleet Assistant", page_icon="🚚", layout="wide")

if "history" not in st.session_state:
    st.session_state.history = []  # list[Turn]

with st.sidebar:
    st.subheader("Session")
    user_id = st.number_input(
        "user_id (thread)",
        min_value=1,
        value=1,
        step=1,
        help=(
            "Conversation memory is keyed by this id (LangGraph SQLite "
            "checkpointer). Change it to start a fresh, isolated thread."
        ),
    )
    st.caption(f"Model: `{settings.ollama_model}`")
    st.caption(f"Ollama: `{settings.ollama_base_url}`")
    st.caption(f"Pitstrack: `{settings.pitstrack_base_url}`")

    if st.session_state.history:
        times = [turn.elapsed_ms for turn in st.session_state.history]
        st.subheader("Response time (ms)")
        st.metric("Last", f"{times[-1]:,.0f}")
        st.metric("Average", f"{sum(times) / len(times):,.0f}")
        st.metric("Slowest", f"{max(times):,.0f}")

    if st.button("Clear history (this view only)"):
        st.session_state.history = []
        st.rerun()

st.title("🚚 Fleet Assistant — test console")
st.caption(
    "Talks directly to the LangChain/LangGraph vehicle agent. Response time "
    "is the agent's own measured `elapsed_ms` for that call, shown after "
    "every reply."
)

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn.query)
    with st.chat_message("assistant"):
        st.write(turn.answer)
        badges = [f"⏱️ {turn.elapsed_ms:,.0f} ms", f"mode: {turn.mode}"]
        if turn.tools_used:
            badges.append("tools: " + ", ".join(turn.tools_used))
        if turn.tool_failures:
            badges.append(f"⚠️ {turn.tool_failures} tool failure(s)")
        st.caption(" · ".join(badges))

query = st.chat_input("Ask about vehicles, fleet status, drivers, or working hours…")

if query:
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("_Thinking…_")
        wall_start = time.perf_counter()
        result = langchain_agent.chat(query, int(user_id))
        wall_elapsed_ms = (time.perf_counter() - wall_start) * 1_000

        meta = result.get("meta", {})
        answer = result.get("answer", "")
        elapsed_ms = meta.get("elapsed_ms", wall_elapsed_ms)

        placeholder.write(answer)
        badges = [f"⏱️ {elapsed_ms:,.0f} ms", f"mode: {meta.get('mode', '?')}"]
        tools_used = meta.get("tools_used") or []
        if tools_used:
            badges.append("tools: " + ", ".join(tools_used))
        tool_failures = meta.get("tool_failures", 0)
        if tool_failures:
            badges.append(f"⚠️ {tool_failures} tool failure(s)")
        st.caption(" · ".join(badges))

    st.session_state.history.append(
        Turn(
            query=query,
            answer=answer,
            elapsed_ms=elapsed_ms,
            mode=meta.get("mode", "?"),
            tools_used=tools_used,
            tool_failures=tool_failures,
        )
    )
    st.rerun()

if st.session_state.history:
    st.subheader("Query log")
    st.dataframe(
        [
            {
                "#": i + 1,
                "query": turn.query,
                "response time (ms)": round(turn.elapsed_ms, 1),
                "mode": turn.mode,
                "tools_used": ", ".join(turn.tools_used) or "—",
                "tool_failures": turn.tool_failures,
            }
            for i, turn in enumerate(st.session_state.history)
        ],
        use_container_width=True,
        hide_index=True,
    )
