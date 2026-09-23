from api_client import LibraryAPIClient


def main():
    print("=== Conversation API Test ===")

    # Login interactively.
    api = LibraryAPIClient(interactive=True)

    # ---------------------------------------------------------
    # 1. Create conversation
    # ---------------------------------------------------------

    print("\n=== 1. Create conversation ===")

    conversation = api.create_conversation(
        title="AI Agent Test Conversation"
    )

    print(conversation)

    conversation_id = conversation["conversation"]["id"]

    print(f"Conversation ID: {conversation_id}")

    # ---------------------------------------------------------
    # 2. Add user message
    # ---------------------------------------------------------

    print("\n=== 2. Add user message ===")

    user_message = api.add_conversation_message(
        conversation_id=conversation_id,
        role="user",
        content="Show me the available books.",
    )

    print(user_message)

    # ---------------------------------------------------------
    # 3. Add assistant message
    # ---------------------------------------------------------

    print("\n=== 3. Add assistant message ===")

    assistant_message = api.add_conversation_message(
        conversation_id=conversation_id,
        role="assistant",
        content="Sure, I will show you the available books.",
    )

    print(assistant_message)

    # ---------------------------------------------------------
    # 4. Get conversation
    # ---------------------------------------------------------

    print("\n=== 4. Get conversation ===")

    saved_conversation = api.get_conversation(
        conversation_id
    )

    print(saved_conversation)

    # ---------------------------------------------------------
    # 5. List conversations
    # ---------------------------------------------------------

    print("\n=== 5. List conversations ===")

    conversations = api.get_conversations()

    print(conversations)

    print("\n=== Test completed successfully ===")


if __name__ == "__main__":
    main()
