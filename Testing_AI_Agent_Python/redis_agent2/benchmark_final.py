"""
Final Performance Benchmark
============================

Benchmarks the current Library Assistant architecture:

    User Request
        ↓
    Smart Router
        ↓
    ├── Direct Tool + Redis
    │
    └── LLM Agent + Redis Tools
            ↓
        Ollama / Qwen3 1.7B

The benchmark does NOT modify the agent architecture.

It measures:
- Total response time
- Route/group
- Average
- Median
- Minimum
- Maximum
- Standard deviation
- Direct vs LLM performance
- Individual request performance

Results are saved to CSV.
"""

import csv
import statistics
import time
from datetime import datetime
from pathlib import Path

from routed_agent import invoke_routed_agent


# ============================================================
# Configuration
# ============================================================

WARMUP_RUNS = 1
MEASURED_RUNS = 3

OUTPUT_DIR = Path(__file__).resolve().parent / "benchmark_results"

CSV_FILE = OUTPUT_DIR / "final_benchmark_results.csv"
SUMMARY_FILE = OUTPUT_DIR / "final_benchmark_summary.csv"


# ============================================================
# Benchmark cases
# ============================================================

BENCHMARK_CASES = [
    {
        "name": "Show all books",
        "request": "show all books",
        "category": "DIRECT",
        "description": "Direct books listing + Redis cache",
    },
    {
        "name": "Show available books",
        "request": "show available books",
        "category": "DIRECT",
        "description": "Direct available-books listing + Redis cache",
    },
    {
        "name": "Show all members",
        "request": "show all members",
        "category": "DIRECT",
        "description": "Direct member listing + Redis cache",
    },
    {
        "name": "My profile",
        "request": "show my profile",
        "category": "DIRECT",
        "description": "Direct authenticated profile lookup",
    },
    {
        "name": "My borrowed books",
        "request": "what have I borrowed?",
        "category": "DIRECT",
        "description": "Direct borrowed-books lookup + Redis",
    },
    {
        "name": "My borrowing history",
        "request": "show my borrowing history",
        "category": "DIRECT",
        "description": "Direct borrowing-history lookup + Redis",
    },
    {
        "name": "Search Python books",
        "request": "search for Python books",
        "category": "LLM",
        "description": "Books agent + tool calling",
    },
    {
        "name": "Book details",
        "request": "show details about Sapiens",
        "category": "LLM",
        "description": "Books agent + book details tool",
    },
    {
        "name": "General greeting",
        "request": "hello",
        "category": "LLM",
        "description": "General agent",
    },
]


# ============================================================
# Utility functions
# ============================================================

def ensure_output_directory():
    """Create benchmark output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def percentile(values, percent):
    """
    Calculate a percentile without requiring NumPy.
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)

    if len(sorted_values) == 1:
        return sorted_values[0]

    index = (len(sorted_values) - 1) * (percent / 100)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)

    fraction = index - lower

    return (
        sorted_values[lower]
        + (sorted_values[upper] - sorted_values[lower]) * fraction
    )


def format_seconds(value):
    """Format seconds for console output."""
    return f"{value:.3f}s"


def calculate_statistics(times):
    """Calculate statistical metrics."""
    return {
        "count": len(times),
        "average": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "std_dev": (
            statistics.stdev(times)
            if len(times) > 1
            else 0.0
        ),
        "p95": percentile(times, 95),
    }


def calculate_improvement(baseline, optimized):
    """
    Calculate percentage improvement.

    Example:
        baseline = 10
        optimized = 2

        improvement = 80%
    """
    if baseline == 0:
        return 0.0

    return ((baseline - optimized) / baseline) * 100


# ============================================================
# Execute one request
# ============================================================

def execute_request(request, conversation_id=None):
    """
    Execute one routed-agent request and measure total latency.

    The timer intentionally starts immediately before
    invoke_routed_agent() and ends immediately after it.

    This measures the user-visible end-to-end response time
    of the current Python agent architecture.
    """

    start = time.perf_counter()

    result, group = invoke_routed_agent(
        user_message=request,
        conversation_id=conversation_id,
    )

    end = time.perf_counter()

    elapsed = end - start

    return {
        "response": result,
        "group": group,
        "elapsed": elapsed,
    }


# ============================================================
# Warm-up
# ============================================================

def warm_up():
    """
    Warm up Ollama/model and Python components.

    This prevents the first request from dominating the
    benchmark because of model loading.
    """

    print()
    print("=" * 70)
    print("WARM-UP")
    print("=" * 70)

    for i in range(WARMUP_RUNS):
        print(f"Warm-up {i + 1}/{WARMUP_RUNS}...")

        start = time.perf_counter()

        try:
            result, group = invoke_routed_agent(
                user_message="hello",
                conversation_id=None,
            )

            elapsed = time.perf_counter() - start

            print(
                f"  Group: {group}"
                f" | Time: {format_seconds(elapsed)}"
            )

        except Exception as exc:
            print(f"  Warm-up failed: {exc}")

    print("Warm-up completed.")


# ============================================================
# Benchmark one case
# ============================================================

def benchmark_case(case):
    """
    Run one benchmark case multiple times.
    """

    name = case["name"]
    request = case["request"]
    expected_category = case["category"]

    print()
    print("-" * 70)
    print(f"TEST: {name}")
    print(f"Request: {request}")
    print(f"Expected category: {expected_category}")
    print("-" * 70)

    times = []
    groups = []
    responses = []

    for run_number in range(1, MEASURED_RUNS + 1):

        print(
            f"Run {run_number}/{MEASURED_RUNS}...",
            end=" ",
            flush=True,
        )

        try:
            result = execute_request(request)

            elapsed = result["elapsed"]
            group = result["group"]
            response = result["response"]

            times.append(elapsed)
            groups.append(group)
            responses.append(response)

            print(
                f"{format_seconds(elapsed)}"
                f" | group={group}"
            )

        except Exception as exc:
            print(f"FAILED: {exc}")

    if not times:
        return None

    stats = calculate_statistics(times)

    actual_group = groups[-1] if groups else "UNKNOWN"

    print()
    print("Statistics:")
    print(f"  Average : {format_seconds(stats['average'])}")
    print(f"  Median  : {format_seconds(stats['median'])}")
    print(f"  Min     : {format_seconds(stats['min'])}")
    print(f"  Max     : {format_seconds(stats['max'])}")
    print(f"  Std Dev : {format_seconds(stats['std_dev'])}")
    print(f"  P95     : {format_seconds(stats['p95'])}")
    print(f"  Group   : {actual_group}")

    return {
        "name": name,
        "request": request,
        "expected_category": expected_category,
        "actual_group": actual_group,
        "description": case["description"],
        "count": stats["count"],
        "average": stats["average"],
        "median": stats["median"],
        "min": stats["min"],
        "max": stats["max"],
        "std_dev": stats["std_dev"],
        "p95": stats["p95"],
        "times": times,
        "response": responses[-1] if responses else "",
    }


# ============================================================
# Benchmark all cases
# ============================================================

def run_benchmark():
    """
    Run the complete final benchmark.
    """

    ensure_output_directory()

    print()
    print("=" * 70)
    print("LIBRARY ASSISTANT - FINAL PERFORMANCE BENCHMARK")
    print("=" * 70)

    print()
    print("Architecture:")
    print("  Smart Router")
    print("       ↓")
    print("  Direct Tools + Redis")
    print("       OR")
    print("  LangChain Agent + Ollama")
    print()
    print(f"Warm-up runs : {WARMUP_RUNS}")
    print(f"Measured runs: {MEASURED_RUNS}")
    print(f"Output       : {OUTPUT_DIR}")

    warm_up()

    results = []

    benchmark_start = time.perf_counter()

    for case in BENCHMARK_CASES:

        result = benchmark_case(case)

        if result is not None:
            results.append(result)

    benchmark_elapsed = time.perf_counter() - benchmark_start

    print()
    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

    print(
        f"Total benchmark time: "
        f"{format_seconds(benchmark_elapsed)}"
    )

    return results


# ============================================================
# Overall statistics
# ============================================================

def calculate_overall_statistics(results):
    """
    Calculate overall statistics for all benchmark requests.
    """

    all_times = []

    for result in results:
        all_times.extend(result["times"])

    if not all_times:
        return None

    return calculate_statistics(all_times)


# ============================================================
# Category statistics
# ============================================================

def calculate_category_statistics(results):
    """
    Calculate statistics separately for:

        DIRECT
        LLM
    """

    categories = {}

    for result in results:

        category = result["expected_category"]

        if category not in categories:
            categories[category] = []

        categories[category].extend(result["times"])

    output = {}

    for category, times in categories.items():
        output[category] = calculate_statistics(times)

    return output


# ============================================================
# Print final report
# ============================================================

def print_final_report(results):
    """
    Print the final human-readable benchmark report.
    """

    if not results:
        print("No benchmark results available.")
        return

    overall = calculate_overall_statistics(results)
    categories = calculate_category_statistics(results)

    print()
    print()
    print("=" * 80)
    print("FINAL PERFORMANCE REPORT")
    print("=" * 80)

    # --------------------------------------------------------
    # Per-request results
    # --------------------------------------------------------

    print()
    print("PER-REQUEST RESULTS")
    print("-" * 80)

    print(
        f"{'Request':<28}"
        f"{'Type':<10}"
        f"{'Avg':>10}"
        f"{'Median':>10}"
        f"{'Min':>10}"
        f"{'Max':>10}"
    )

    print("-" * 80)

    for result in results:

        print(
            f"{result['name']:<28}"
            f"{result['expected_category']:<10}"
            f"{format_seconds(result['average']):>10}"
            f"{format_seconds(result['median']):>10}"
            f"{format_seconds(result['min']):>10}"
            f"{format_seconds(result['max']):>10}"
        )

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    print()
    print("OVERALL")
    print("-" * 80)

    print(
        f"Requests measured : {overall['count']}"
    )

    print(
        f"Average           : "
        f"{format_seconds(overall['average'])}"
    )

    print(
        f"Median            : "
        f"{format_seconds(overall['median'])}"
    )

    print(
        f"Minimum           : "
        f"{format_seconds(overall['min'])}"
    )

    print(
        f"Maximum           : "
        f"{format_seconds(overall['max'])}"
    )

    print(
        f"Std deviation     : "
        f"{format_seconds(overall['std_dev'])}"
    )

    print(
        f"P95               : "
        f"{format_seconds(overall['p95'])}"
    )

    # --------------------------------------------------------
    # Category comparison
    # --------------------------------------------------------

    print()
    print("DIRECT vs LLM")
    print("-" * 80)

    for category, stats in categories.items():

        print()
        print(category)

        print(
            f"  Average : "
            f"{format_seconds(stats['average'])}"
        )

        print(
            f"  Median  : "
            f"{format_seconds(stats['median'])}"
        )

        print(
            f"  Min     : "
            f"{format_seconds(stats['min'])}"
        )

        print(
            f"  Max     : "
            f"{format_seconds(stats['max'])}"
        )

        print(
            f"  P95     : "
            f"{format_seconds(stats['p95'])}"
        )

    # --------------------------------------------------------
    # Direct vs LLM improvement
    # --------------------------------------------------------

    if "DIRECT" in categories and "LLM" in categories:

        direct_avg = categories["DIRECT"]["average"]
        llm_avg = categories["LLM"]["average"]

        print()
        print("LATENCY DIFFERENCE")
        print("-" * 80)

        if llm_avg > direct_avg:

            difference = calculate_improvement(
                llm_avg,
                direct_avg,
            )

            print(
                f"Direct requests are approximately "
                f"{difference:.2f}% faster than LLM requests."
            )

        else:

            difference = calculate_improvement(
                direct_avg,
                llm_avg,
            )

            print(
                f"LLM requests are approximately "
                f"{difference:.2f}% faster than Direct requests."
            )

    print()
    print("=" * 80)


# ============================================================
# Save detailed CSV
# ============================================================

def save_detailed_csv(results):
    """
    Save every measured run to CSV.
    """

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "timestamp",
                "request_name",
                "request",
                "expected_category",
                "actual_group",
                "run",
                "response_time_seconds",
            ]
        )

        timestamp = datetime.now().isoformat()

        for result in results:

            for index, elapsed in enumerate(
                result["times"],
                start=1,
            ):

                writer.writerow(
                    [
                        timestamp,
                        result["name"],
                        result["request"],
                        result["expected_category"],
                        result["actual_group"],
                        index,
                        round(elapsed, 6),
                    ]
                )

    print()
    print(f"Detailed results saved to:")
    print(CSV_FILE)


# ============================================================
# Save summary CSV
# ============================================================

def save_summary_csv(results):
    """
    Save one summary row per benchmark case.
    """

    with open(
        SUMMARY_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "request_name",
                "request",
                "category",
                "actual_group",
                "average_seconds",
                "median_seconds",
                "min_seconds",
                "max_seconds",
                "std_dev_seconds",
                "p95_seconds",
            ]
        )

        for result in results:

            writer.writerow(
                [
                    result["name"],
                    result["request"],
                    result["expected_category"],
                    result["actual_group"],
                    round(result["average"], 6),
                    round(result["median"], 6),
                    round(result["min"], 6),
                    round(result["max"], 6),
                    round(result["std_dev"], 6),
                    round(result["p95"], 6),
                ]
            )

    print()
    print(f"Summary saved to:")
    print(SUMMARY_FILE)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    results = run_benchmark()

    print_final_report(results)

    save_detailed_csv(results)

    save_summary_csv(results)

    print()
    print("Final benchmark finished successfully.")
