import time

import streamlit as st

from redis_agent.agent_redis import agent

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Library Assistant - Redis",
    page_icon="📚",
    layout="centered",
)


# ---------------------------------------------------------
# Page title
# ---------------------------------------------------------

st.title("📚 Library Assistant")
st.caption("LangChain + Ollama + Redis")


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------
# Display previous messages
# ---------------------------------------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant" and "response_time" in message:
            st.caption(
                f"⏱️ Response time: {message['response_time']:.2f} seconds"
            )


# ---------------------------------------------------------
# Chat input
# ---------------------------------------------------------

user_input = st.chat_input("Ask something about the library...")


if user_input:

    # Show user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    # -----------------------------------------------------
    # Run agent and measure response time
    # -----------------------------------------------------

    start_time = time.perf_counter()

    try:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_input,
                    }
                ]
            }
        )

        total_time = time.perf_counter() - start_time

        # Get final assistant response
        assistant_message = result["messages"][-1].content

        # -------------------------------------------------
        # Inspect agent messages
        # -------------------------------------------------

        tool_calls = []

        for message in result["messages"]:
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append(
                        {
                            "name": tool_call.get("name", "unknown"),
                        }
                    )

    except Exception as e:
        total_time = time.perf_counter() - start_time
        assistant_message = f"Error: {e}"
        tool_calls = []


    # -----------------------------------------------------
    # Display assistant response
    # -----------------------------------------------------

    with st.chat_message("assistant"):
        st.markdown(assistant_message)

        st.caption(
            f"⏱️ Total response time: {total_time:.2f} seconds"
        )

        if tool_calls:
            st.write("🔧 Tools used:")

            for tool in tool_calls:
                st.write(f"- `{tool['name']}`")

        else:
            st.write("🔧 No tools detected")


    # Save assistant message
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_message,
            "response_time": total_time,
        }
    )
