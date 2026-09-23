import time

import streamlit as st

from routed_agent import invoke_routed_agent
from api_client import LibraryAPIClient
from conversation_memory import ConversationMemory


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Library Assistant - Routed",
    page_icon="📚",
    layout="centered",
)


# ---------------------------------------------------------
# Page title
# ---------------------------------------------------------

st.title("📚 Library Assistant")
st.caption("LangChain + Ollama + Redis + Smart Routing")


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------
# Create one persistent conversation for this Streamlit
# session
# ---------------------------------------------------------

if "conversation_id" not in st.session_state:

    api_client = LibraryAPIClient(interactive=True)

    memory = ConversationMemory(api_client)

    conversation_id = memory.create(
        title="Library Assistant Conversation"
    )

    st.session_state.conversation_id = conversation_id

    print(
        f"[STREAMLIT] Created conversation: "
        f"{conversation_id}"
    )


# ---------------------------------------------------------
# Get current conversation ID
# ---------------------------------------------------------

conversation_id = st.session_state.conversation_id


# ---------------------------------------------------------
# Display previous messages
# ---------------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        # Show response time only for assistant messages
        if message["role"] == "assistant":

            response_time = message.get("response_time")
            route = message.get("route")

            if response_time is not None:

                if route:
                    st.caption(
                        f"Route: `{route}` · "
                        f"Response time: `{response_time:.3f}s`"
                    )

                else:
                    st.caption(
                        f"Response time: `{response_time:.3f}s`"
                    )


# ---------------------------------------------------------
# Chat input
# ---------------------------------------------------------

user_message = st.chat_input(
    "Ask about books, members, borrowing, or your account..."
)


if user_message:

    # -----------------------------------------------------
    # Display user message
    # -----------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_message)

    # -----------------------------------------------------
    # Run routed agent
    # -----------------------------------------------------

    start_time = time.perf_counter()

    try:

        result, group = invoke_routed_agent(
            user_message=user_message,
            conversation_id=conversation_id,
        )

        # Calculate response time
        elapsed = time.perf_counter() - start_time

        # -------------------------------------------------
        # Extract response
        # -------------------------------------------------

        if result.get("error"):

            response = result["error"]

        elif result.get("direct"):

            response = result.get(
                "response",
                "No response returned.",
            )

        else:

            messages = result.get(
                "messages",
                []
            )

            if messages:

                last_message = messages[-1]

                response = getattr(
                    last_message,
                    "content",
                    str(last_message),
                )

            else:

                response = "No response returned."

        # -------------------------------------------------
        # Display assistant response
        # -------------------------------------------------

        with st.chat_message("assistant"):

            st.markdown(response)

            st.caption(
                f"Route: `{group}` · "
                f"Response time: `{elapsed:.3f}s`"
            )

        # -------------------------------------------------
        # Save assistant message + response time
        # -------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
                "response_time": elapsed,
                "route": group,
            }
        )

    except Exception as e:

        # Calculate response time even when an error occurs
        elapsed = time.perf_counter() - start_time

        response = (
            f"Something went wrong:\n\n"
            f"`{e}`"
        )

        # -------------------------------------------------
        # Display error
        # -------------------------------------------------

        with st.chat_message("assistant"):

            st.error(response)

            st.caption(
                f"Response time: `{elapsed:.3f}s`"
            )

        # -------------------------------------------------
        # Save error + response time
        # -------------------------------------------------

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
                "response_time": elapsed,
                "route": "error",
            }
        )
