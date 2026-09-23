import sys
import time
from pathlib import Path
from statistics import mean, median


# ---------------------------------------------------------
# Project root
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# Imports
# ---------------------------------------------------------

from routed_agent import invoke_routed_agent


# ---------------------------------------------------------
# Support the existing no-Redis import structure
# ---------------------------------------------------------

NO_REDIS_AGENT_DIR = PROJECT_ROOT / "no_redis_agent"

if str(NO_REDIS_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(NO_REDIS_AGENT_DIR))


from no_redis_agent.agent_no_redis import agent as original_agent


# ---------------------------------------------------------
# Original agent wrapper
# ---------------------------------------------------------

def invoke_original_agent(user_message: str):
    return original_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        }
    )


# ---------------------------------------------------------
# Test cases
# ---------------------------------------------------------

TEST_CASES = [
    # Direct routing
    "show all books",
    "show available books",
    "my profile",
    "what have I borrowed?",
    "show my borrowing history",
    "list members",
    "show library statistics",
    "show Omar borrowing history",
    "show Sapiens borrowing history",

    # Routed LLM
    "search for Python books",
    "show details about Sapiens",

    # General LLM
    "hello",
]


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

WARMUP_RUNS = 1
MEASURED_RUNS = 3


# ---------------------------------------------------------
# Timing helper
# ---------------------------------------------------------

def measure(func, request):
    start = time.perf_counter()

    try:
        result = func(request)
        elapsed = time.perf_counter() - start

        return elapsed, result, None

    except Exception as e:
        elapsed = time.perf_counter() - start

        return elapsed, None, e


# ---------------------------------------------------------
# Run benchmark for one function
# ---------------------------------------------------------

def benchmark_function(func, request, label):

    print(f"\n[{label}]")

    # -----------------------------------------------------
    # Warm-up
    # -----------------------------------------------------

    print("Warm-up...")

    warmup_time, _, warmup_error = measure(
        func,
        request,
    )

    if warmup_error:
        print(
            f"Warm-up ERROR: "
            f"{type(warmup_error).__name__}: "
            f"{warmup_error}"
        )

        return None

    print(
        f"Warm-up time: "
        f"{warmup_time:.3f}s"
    )

    # -----------------------------------------------------
    # Measured runs
    # -----------------------------------------------------

    times = []

    for run_number in range(
        1,
        MEASURED_RUNS + 1,
    ):

        elapsed, _, error = measure(
            func,
            request,
        )

        if error:

            print(
                f"Run {run_number}: ERROR: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            continue

        times.append(elapsed)

        print(
            f"Run {run_number}: "
            f"{elapsed:.3f}s"
        )

    if not times:
        return None

    return {
        "times": times,
        "average": mean(times),
        "median": median(times),
        "minimum": min(times),
        "maximum": max(times),
    }


# ---------------------------------------------------------
# Detect routed execution type
# ---------------------------------------------------------

def get_routing_info(result):

    if not isinstance(result, tuple):
        return None, None

    result_data, group = result

    if not isinstance(result_data, dict):
        return None, group

    if result_data.get("direct"):
        execution = "DIRECT"
    else:
        execution = "LLM"

    return execution, group


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("\n")
    print("=" * 100)
    print("ROUTING PERFORMANCE BENCHMARK V2")
    print("=" * 100)

    print(
        f"Warm-up runs:   {WARMUP_RUNS}"
    )

    print(
        f"Measured runs:  {MEASURED_RUNS}"
    )

    print("=" * 100)

    all_results = []

    # -----------------------------------------------------
    # Test every request
    # -----------------------------------------------------

    for request in TEST_CASES:

        print("\n")
        print("-" * 100)
        print(f"REQUEST: {request}")
        print("-" * 100)

        # =================================================
        # Original agent
        # =================================================

        original = benchmark_function(
            invoke_original_agent,
            request,
            "ORIGINAL AGENT",
        )

        # =================================================
        # Routed agent
        # =================================================

        routed = benchmark_function(
            invoke_routed_agent,
            request,
            "ROUTED AGENT",
        )

        # -------------------------------------------------
        # Routing information
        # -------------------------------------------------

        execution_type = None
        group = None

        if routed:

            # Run one additional invocation only to inspect
            # the returned routing metadata.
            #
            # This does not affect the measured timings.
            _, routing_result, routing_error = measure(
                invoke_routed_agent,
                request,
            )

            if not routing_error:

                execution_type, group = get_routing_info(
                    routing_result
                )

        # -------------------------------------------------
        # Compare
        # -------------------------------------------------

        if original and routed:

            improvement = (
                (
                    original["average"]
                    - routed["average"]
                )
                / original["average"]
            ) * 100

            print("\nRESULT")

            print(
                f"Original average : "
                f"{original['average']:.3f}s"
            )

            print(
                f"Routed average   : "
                f"{routed['average']:.3f}s"
            )

            print(
                f"Original median  : "
                f"{original['median']:.3f}s"
            )

            print(
                f"Routed median    : "
                f"{routed['median']:.3f}s"
            )

            print(
                f"Original min     : "
                f"{original['minimum']:.3f}s"
            )

            print(
                f"Routed min       : "
                f"{routed['minimum']:.3f}s"
            )

            print(
                f"Original max     : "
                f"{original['maximum']:.3f}s"
            )

            print(
                f"Routed max       : "
                f"{routed['maximum']:.3f}s"
            )

            print(
                f"Improvement      : "
                f"{improvement:.2f}%"
            )

            if execution_type:
                print(
                    f"Execution        : "
                    f"{execution_type}"
                )

            if group:
                print(
                    f"Group            : "
                    f"{group}"
                )

            all_results.append(
                {
                    "request": request,
                    "execution": execution_type,
                    "group": group,
                    "original_average": original["average"],
                    "routed_average": routed["average"],
                    "improvement": improvement,
                }
            )

    # =====================================================
    # Overall summary
    # =====================================================

    print("\n\n")
    print("=" * 100)
    print("OVERALL SUMMARY")
    print("=" * 100)

    if not all_results:
        print("No successful benchmark results.")
        return

    original_average = mean(
        item["original_average"]
        for item in all_results
    )

    routed_average = mean(
        item["routed_average"]
        for item in all_results
    )

    overall_improvement = (
        (original_average - routed_average)
        / original_average
    ) * 100

    print(
        f"Original average: "
        f"{original_average:.3f}s"
    )

    print(
        f"Routed average:   "
        f"{routed_average:.3f}s"
    )

    print(
        f"Overall improvement: "
        f"{overall_improvement:.2f}%"
    )

    # =====================================================
    # Direct routing summary
    # =====================================================

    direct_results = [
        item
        for item in all_results
        if item["execution"] == "DIRECT"
    ]

    llm_results = [
        item
        for item in all_results
        if item["execution"] == "LLM"
    ]

    print("\n")
    print("=" * 100)
    print("DIRECT ROUTING")
    print("=" * 100)

    if direct_results:

        direct_original = mean(
            item["original_average"]
            for item in direct_results
        )

        direct_routed = mean(
            item["routed_average"]
            for item in direct_results
        )

        direct_improvement = (
            (direct_original - direct_routed)
            / direct_original
        ) * 100

        print(
            f"Requests: "
            f"{len(direct_results)}"
        )

        print(
            f"Original average: "
            f"{direct_original:.3f}s"
        )

        print(
            f"Routed average:   "
            f"{direct_routed:.3f}s"
        )

        print(
            f"Improvement:      "
            f"{direct_improvement:.2f}%"
        )

    # =====================================================
    # Routed LLM summary
    # =====================================================

    print("\n")
    print("=" * 100)
    print("ROUTED LLM")
    print("=" * 100)

    if llm_results:

        llm_original = mean(
            item["original_average"]
            for item in llm_results
        )

        llm_routed = mean(
            item["routed_average"]
            for item in llm_results
        )

        llm_improvement = (
            (llm_original - llm_routed)
            / llm_original
        ) * 100

        print(
            f"Requests: "
            f"{len(llm_results)}"
        )

        print(
            f"Original average: "
            f"{llm_original:.3f}s"
        )

        print(
            f"Routed average:   "
            f"{llm_routed:.3f}s"
        )

        print(
            f"Improvement:      "
            f"{llm_improvement:.2f}%"
        )

    # =====================================================
    # Detailed table
    # =====================================================

    print("\n")
    print("=" * 100)
    print("DETAILED RESULTS")
    print("=" * 100)

    print(
        f"{'Request':35} "
        f"{'Type':8} "
        f"{'Original':>12} "
        f"{'Routed':>12} "
        f"{'Improve':>12}"
    )

    print("-" * 100)

    for item in all_results:

        print(
            f"{item['request'][:35]:35} "
            f"{str(item['execution']):8} "
            f"{item['original_average']:>10.3f}s "
            f"{item['routed_average']:>10.3f}s "
            f"{item['improvement']:>10.2f}%"
        )

    print("=" * 100)


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    main()

