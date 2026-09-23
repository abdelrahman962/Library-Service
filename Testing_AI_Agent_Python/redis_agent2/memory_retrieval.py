import re

try:
    from .session_memory import get_recent_memory
except ImportError:
    from session_memory import get_recent_memory
def _clean_text(text: str) -> str:
    """Normalize whitespace and remove Markdown formatting."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_compact_memory(
    conversation_id: int | str,
    max_interactions: int = 3,
    max_chars: int = 1200,
) -> str:
    """
    Retrieve recent conversation memory in a compact form.

    This is intentionally simple for Step 4.
    It does not use embeddings or another LLM.
    """

    recent_memory = get_recent_memory(
        conversation_id,
        max_interactions=max_interactions,
    )

    if not recent_memory:
        return ""

    lines = recent_memory.splitlines()

    memories: list[str] = []

    current_user = None
    current_tool = None
    current_tool_result = None
    current_assistant = None

    def save_interaction():
        nonlocal current_user
        nonlocal current_tool
        nonlocal current_tool_result
        nonlocal current_assistant

        if current_user:
            memories.append(
                f"User previously asked: {_clean_text(current_user)}"
            )

        if current_tool and current_tool_result:
            result = _clean_text(current_tool_result)

            # Keep tool results compact.
            if len(result) > 500:
                result = result[:500] + "..."

            memories.append(
                f"Library result from {current_tool}: {result}"
            )

        if current_assistant:
            cleaned_assistant = _clean_text(current_assistant)

            # Ignore assistant messages that are actually
            # serialized tool calls.
            if not (
                cleaned_assistant.startswith("{")
                and (
                    '"name"' in cleaned_assistant
                    or '"arguments"' in cleaned_assistant
                )
            ):
                memories.append(
                    f"Assistant previously answered: "
                    f"{cleaned_assistant}"
                )
        current_user = None
        current_tool = None
        current_tool_result = None
        current_assistant = None

    section = None

    for line in lines:
        line = line.strip()

        if line.startswith("## ") and not line.startswith("### "):
            if current_user or current_tool or current_assistant:
                save_interaction()

        elif line == "### User":
            section = "user"

        elif line == "### Tool":
            section = "tool"

        elif line == "### Assistant":
            section = "assistant"

        elif line.startswith("**") and line.endswith("**"):
            if section == "tool":
                current_tool = line.strip("*")

        elif line == "**Result:**":
            section = "tool_result"

        elif line:
            if section == "user":
                current_user = (
                    f"{current_user or ''} {line}"
                ).strip()

            elif section == "tool_result":
                current_tool_result = (
                    f"{current_tool_result or ''} {line}"
                ).strip()

            elif section == "assistant":
                current_assistant = (
                    f"{current_assistant or ''} {line}"
                ).strip()

    # Save final interaction.
    if current_user or current_tool or current_assistant:
        save_interaction()

    memory = "\n".join(
        f"- {item}"
        for item in memories
    )

    if len(memory) > max_chars:
        memory = memory[:max_chars].rstrip() + "..."

    return memory
