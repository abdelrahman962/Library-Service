import time

from redis_agent2.agent_redis import invoke_library_agent


TEST_REQUESTS = [
    "hello",
    "show all books",
    "show all available books",
    "show all borrowed books",
    "what is my name?",
]


def run_benchmark():
    print("=" * 70)
    print("LIBRARY AGENT BENCHMARK")
    print("=" * 70)

    thread_id = "benchmark-thread"

    conversation_id = None

    for request in TEST_REQUESTS:
        print("\n" + "-" * 70)
        print(f"REQUEST: {request}")
        print("-" * 70)

        start = time.perf_counter()

        try:
            result, conversation_id, tool_calls = invoke_library_agent(
                user_input=request,
                thread_id=thread_id,
                conversation_id=conversation_id,
            )

            total_time = time.perf_counter() - start

            assistant_message = result["messages"][-1].content

            print(f"\nANSWER: {assistant_message}")

            print(f"\nTOOLS:")
            if tool_calls:
                for tool in tool_calls:
                    print(f"  - {tool['name']}")
            else:
                print("  - None")

            print(f"\nTOTAL TIME: {total_time:.2f}s")

        except Exception as e:
            total_time = time.perf_counter() - start

            print(f"\nERROR: {e}")
            print(f"TOTAL TIME: {total_time:.2f}s")

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
