import sys
import time
from pathlib import Path
from statistics import mean


# ---------------------------------------------------------
# Project root
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# Imports
# ---------------------------------------------------------
# ---------------------------------------------------------
# Imports
# ---------------------------------------------------------

from routed_agent import invoke_routed_agent


# The original no-Redis agent imports `tools_no_redis`
# as a top-level module. Add its directory to sys.path
# so we can import it without modifying the original agent.
NO_REDIS_AGENT_DIR = PROJECT_ROOT / "no_redis_agent"

if str(NO_REDIS_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(NO_REDIS_AGENT_DIR))


from no_redis_agent.agent_no_redis import agent as original_agent

# ---------------------------------------------------------
# Original agent wrapper
# ---------------------------------------------------------

def invoke_original_agent(user_message: str):
    """
    Invoke the original no-Redis LangChain agent.

    The original agent exposes an `agent` object,
    not an `invoke_agent()` function.
    """

    result = original_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        }
    )

    return result


# ---------------------------------------------------------
# Test cases
# ---------------------------------------------------------

# These are intentionally read-only requests.
#
# We do NOT include borrow/return requests because they
# modify the database and could make repeated benchmarks
# inconsistent.

TEST_CASES = [
    # -----------------------------------------------------
    # Requests that the routed agent can execute directly
    # -----------------------------------------------------

    "show all books",
    "show available books",
    "my profile",
    "what have I borrowed?",
    "show my borrowing history",
    "list members",
    "show library statistics",
    "show Omar borrowing history",
    "show Sapiens borrowing history",

    # -----------------------------------------------------
    # Requests that require the LLM + tools
    # -----------------------------------------------------

    "search for Python books",
    "show details about Sapiens",

    # -----------------------------------------------------
    # General conversation
    # -----------------------------------------------------

    "hello",
]


# ---------------------------------------------------------
# Benchmark helper
# ---------------------------------------------------------

def benchmark(func, request):
    """
    Measure how long a function takes to process one request.

    Returns:
        elapsed_time
        result
        error
    """

    start = time.perf_counter()

    try:
        result = func(request)

        elapsed = time.perf_counter() - start

        return elapsed, result, None

    except Exception as e:

        elapsed = time.perf_counter() - start

        return elapsed, None, e


# ---------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------

def main():

    print("\n")
    print("=" * 90)
    print("ORIGINAL AGENT vs ROUTED AGENT PERFORMANCE BENCHMARK")
    print("=" * 90)

    original_times = []
    routed_times = []

    results = []

    # -----------------------------------------------------
    # Run every test case
    # -----------------------------------------------------

    for request in TEST_CASES:

        print("\n" + "-" * 90)
        print(f"Request: {request}")

        # =================================================
        # ORIGINAL AGENT
        # =================================================

        print("\n[ORIGINAL AGENT]")

        original_time, original_result, original_error = benchmark(
            invoke_original_agent,
            request,
        )

        if original_error:

            print(
                f"ERROR: {type(original_error).__name__}: "
                f"{original_error}"
            )

        else:

            print(
                f"Time: {original_time:.3f} seconds"
            )

            original_times.append(original_time)

        # =================================================
        # ROUTED AGENT
        # =================================================

        print("\n[ROUTED AGENT]")

        routed_time, routed_result, routed_error = benchmark(
            invoke_routed_agent,
            request,
        )

        if routed_error:

            print(
                f"ERROR: {type(routed_error).__name__}: "
                f"{routed_error}"
            )

        else:

            print(
                f"Time: {routed_time:.3f} seconds"
            )

            routed_times.append(routed_time)

            # -------------------------------------------------
            # Display routing information
            # -------------------------------------------------

            if isinstance(routed_result, tuple):

                result_data, group = routed_result

                if isinstance(result_data, dict):

                    execution_type = (
                        "DIRECT"
                        if result_data.get("direct")
                        else "LLM"
                    )

                    print(
                        f"Execution: {execution_type}"
                    )

                    print(
                        f"Tool: {result_data.get('tool')}"
                    )

                    print(
                        f"Group: {group}"
                    )

        # =================================================
        # Calculate improvement
        # =================================================

        if not original_error and not routed_error:

            improvement = (
                (original_time - routed_time)
                / original_time
            ) * 100

            print(
                f"\nImprovement: {improvement:.2f}%"
            )

            results.append(
                {
                    "request": request,
                    "original": original_time,
                    "routed": routed_time,
                    "improvement": improvement,
                }
            )

    # =====================================================
    # Summary
    # =====================================================

    print("\n\n")
    print("=" * 90)
    print("BENCHMARK SUMMARY")
    print("=" * 90)

    # -----------------------------------------------------
    # Average times
    # -----------------------------------------------------

    if original_times:

        original_average = mean(original_times)

        print(
            f"Original average: "
            f"{original_average:.3f} seconds"
        )

    if routed_times:

        routed_average = mean(routed_times)

        print(
            f"Routed average:   "
            f"{routed_average:.3f} seconds"
        )

    # -----------------------------------------------------
    # Overall improvement
    # -----------------------------------------------------

    if original_times and routed_times:

        overall_improvement = (
            (mean(original_times) - mean(routed_times))
            / mean(original_times)
        ) * 100

        print(
            f"Overall improvement: "
            f"{overall_improvement:.2f}%"
        )

    # =====================================================
    # Detailed results table
    # =====================================================

    print("\n")

    print(
        f"{'Request':40} "
        f"{'Original':>12} "
        f"{'Routed':>12} "
        f"{'Improvement':>14}"
    )

    print("-" * 90)

    for item in results:

        print(
            f"{item['request'][:40]:40} "
            f"{item['original']:>10.3f}s "
            f"{item['routed']:>10.3f}s "
            f"{item['improvement']:>12.2f}%"
        )

    print("=" * 90)


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
