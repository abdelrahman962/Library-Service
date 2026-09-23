from api_client import LibraryAPIClient
from redis_agent2.conversation_memory import ConversationMemory


def main():
    print("=== Recent Conversation Memory Test ===")

    api = LibraryAPIClient(interactive=True)

    memory = ConversationMemory(api)

    conversation_id = memory.create(
        title="Recent Memory Test"
    )

    print(f"Conversation ID: {conversation_id}")

    # Add several messages
    for i in range(1, 8):
        memory.save_user_message(
            f"User message {i}"
        )

        memory.save_assistant_message(
            f"Assistant response {i}"
        )

    print("\n=== Last 4 messages ===")

    recent_messages = memory.get_recent_messages(limit=4)

    for message in recent_messages:
        print(
            f"[{message['role']}] "
            f"{message['content']}"
        )

    print("\n=== Test completed successfully ===")


if __name__ == "__main__":
    main()
