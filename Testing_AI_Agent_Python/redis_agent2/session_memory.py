from datetime import datetime
from pathlib import Path
# ---------------------------------------------------------
# Memory directory
# ---------------------------------------------------------

MEMORY_DIR =Path(__file__).parent /"memory" /"conversations"
MEMORY_DIR.mkdir(parents =True, exist_ok=True)

# ---------------------------------------------------------
# Get conversation file
# ---------------------------------------------------------

def get_conversation_file(conversation_id: int | str)-> Path:
    """
    Return the Markdown file for a conversation.
    """
    return MEMORY_DIR /f"{conversation_id}.md"


# ---------------------------------------------------------
# Create conversation file
# ---------------------------------------------------------

def initialize_conversation(conversation_id: int|str)-> None:
    """
    Create the conversation memory file if it does not exist.
    """

    file_path = get_conversation_file(conversation_id)

    if not file_path.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = (
            f"# Conversation {conversation_id}\n\n"
            f"Started: {timestamp}\n\n"
        )
        file_path.write_text(
            content,
            encoding="utf-8"
        )


# ---------------------------------------------------------
# Save user message
# ---------------------------------------------------------

def save_user_message(
        conversation_id: int | str,
        message: str,
)->None:
    """
    Append a user message to the conversation memory.
    """

    initialize_conversation(conversation_id)

    file_path = get_conversation_file(conversation_id)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = (
        f"## {timestamp}\n\n"
        f"### User\n"
        f"{message}\n\n"
    )

    with file_path.open("a", encoding="utf-8") as file:
        file.write(content)


# ---------------------------------------------------------
# Save tool action
# ---------------------------------------------------------

def save_tool_result(
    conversation_id: int | str,
    tool_name: str,
    result: str,
) -> None:
    """
    Append a tool call and its result to the conversation memory.
    """
    initialize_conversation(conversation_id)

    file_path = get_conversation_file(conversation_id)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = (
        f"## {timestamp}\n\n"
        f"### Tool\n"
        f"**{tool_name}**\n\n"
        f"**Result:**\n"
        f"{result}\n\n"
    )
    with file_path.open("a", encoding="utf-8") as file :
        file.write(content)

# ---------------------------------------------------------
# Save assistant response
# ---------------------------------------------------------

def save_assistant_message(
    conversation_id: int | str,
    message: str,
) -> None:
    """
    Append the assistant's response to the conversation memory.
    """

    initialize_conversation(conversation_id)

    file_path = get_conversation_file(conversation_id)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = (
        f"## {timestamp}\n\n"
        f"### Assistant\n"
        f"{message}\n\n"
    )

    with file_path.open("a", encoding="utf-8") as file:
        file.write(content)



def get_recent_memory(
    conversation_id: int | str,
    max_interactions: int = 3,
) -> str:
    """
    Read the most recent conversation interactions from Markdown memory.

    This intentionally reads only recent memory instead of the entire file.
    """

    file_path = get_conversation_file(conversation_id)

    if not file_path.exists():
        return ""

    content = file_path.read_text(encoding="utf-8").strip()

    if not content:
        return ""

    sections = content.split("\n## ")

    if len(sections) <= 1:
        return ""

    recent_sections = sections[-max_interactions:]

    memory = "\n## ".join(recent_sections).strip()

    return memory
