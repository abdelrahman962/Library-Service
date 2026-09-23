import sys
import time
import uuid
from pathlib import Path
from typing import Any, cast

import streamlit as st


# ============================================================
# Python path
# ============================================================

_PARENT_DIR = str(Path(__file__).resolve().parent.parent)

if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)


from redis_agent2.agent_redis import invoke_library_agent


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="Library Assistant - Redis",
    page_icon="📚",
    layout="centered",
)


# ============================================================
# Page title
# ============================================================

st.title("📚 Library Assistant")
st.caption("LangChain + Ollama + Redis")


# ============================================================
# Session state
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


# ============================================================
# Display previous messages
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if (
            message["role"] == "assistant"
            and "response_time" in message
        ):
            st.caption(
                f"⏱️ Response time: "
                f"{message['response_time']:.2f} seconds"
            )


# ============================================================
# Chat input
# ============================================================

user_input = st.chat_input(
    "Ask something about the library..."
)


# ============================================================
# Process user message
# ============================================================

if user_input:

    # ---------------------------------------------------------
    # Display user message immediately
    # ---------------------------------------------------------

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    # ---------------------------------------------------------
    # Run agent and measure response time
    # ---------------------------------------------------------

    start_time = time.perf_counter()

    try:

        result, conversation_id, tool_calls = invoke_library_agent(
            user_input=user_input,
            thread_id=st.session_state.thread_id,
            conversation_id=st.session_state.conversation_id,
        )

        total_time = time.perf_counter() - start_time

        # -----------------------------------------------------
        # Save persistent MySQL conversation ID
        # -----------------------------------------------------

        st.session_state.conversation_id = conversation_id

        # -----------------------------------------------------
        # Get final assistant response
        # -----------------------------------------------------

        result = cast(
            dict[str, Any],
            result,
        )

        assistant_message = result["messages"][-1].content



    except Exception as e:

        total_time = time.perf_counter() - start_time

        assistant_message = f"Error: {e}"

        tool_calls = []


    # =========================================================
    # Display assistant response
    # =========================================================

    with st.chat_message("assistant"):

        st.markdown(assistant_message)

        st.caption(
            f"⏱️ Total response time: "
            f"{total_time:.2f} seconds"
        )

        if tool_calls:

            st.write("🔧 Tools used:")

            for tool in tool_calls:

                st.write(
                    f"- `{tool['name']}`"
                )

        else:

            st.write(
                "🔧 No tools detected"
            )


    # =========================================================
    # Save assistant message to Streamlit session state
    # =========================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
            "response_time": total_time,
        }
    )
