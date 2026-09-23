from api_client import LibraryAPIClient
from redis_agent2.conversation_memory import ConversationMemory


def main():
    print("=== Conversation Memory Test ===")

    api = LibraryAPIClient(interactive=True)

    # Create memory manager
    memory = ConversationMemory(api)

    # Create conversation
    conversation_id = memory.create(
        title="Conversation Memory Test"
    )

    print(f"\nConversation created: {conversation_id}")

    # Save user message
    user_message = memory.save_user_message(
        "Show me the available books."
    )

    print("\nUser message saved:")
    print(user_message)

    # Save assistant message
    assistant_message = memory.save_assistant_message(
        "Here are the available books."
    )

    print("\nAssistant message saved:")
    print(assistant_message)

    # Load conversation history
    messages = memory.get_messages()

    print("\nConversation history:")

    for message in messages:
        print(
            f"[{message['role']}] "
            f"{message['content']}"
        )

    print("\n=== Test completed successfully ===")


if __name__ == "__main__":
    main()
