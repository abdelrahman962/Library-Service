"""
Keyword router vs. AI router benchmark.

Compares router_keyword_backup.route_request() (the old classifier,
kept only as a fallback now) against ai_router.classify_route() (the
new one) on both latency and accuracy against an expected-route
table. Mirrors the measure/benchmark_function pattern used in
benchmark_routing_v2.py.
"""

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


from router_keyword_backup import route_request as keyword_route_request
from ai_router import classify_route as ai_classify_route


# ---------------------------------------------------------
# Test cases: (message, expected_route)
# ---------------------------------------------------------

TEST_CASES = [

    # Cases the keyword router handles fine
    ("show all books", "books"),
    ("show available books", "books"),
    ("search for Python books", "books"),
    ("my profile", "user"),
    ("what have I borrowed?", "user"),
    ("borrow Clean Code", "borrowing"),
    ("return Sapiens", "borrowing"),
    ("show library statistics", "admin"),
    ("show Omar borrowing history", "admin"),
    ("hello", "general"),

    # Cases with no literal keyword overlap - where the AI router
    # is expected to outperform keyword matching
    ("Which titles can I take home right now?", "books"),
    ("I'm looking for something to learn Python", "books"),
    ("Could you show me everything in the catalog?", "books"),
    ("Can you tell me what's on my account?", "user"),
    ("I finished reading Clean Code and want to give it back.", "borrowing"),
    ("Can I take this one home with me?", "borrowing"),
    ("Who else has an account here?", "admin"),
    ("what's up?", "general"),
]


# ---------------------------------------------------------
# Timing helper
# ---------------------------------------------------------

def measure(func, message):

    start = time.perf_counter()

    try:
        result = func(message)
        elapsed = time.perf_counter() - start

        return elapsed, result, None

    except Exception as e:
        elapsed = time.perf_counter() - start

        return elapsed, None, e


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("\n")
    print("=" * 100)
    print("KEYWORD ROUTER vs AI ROUTER BENCHMARK")
    print("=" * 100)

    keyword_times = []
    ai_times = []

    keyword_correct = 0
    ai_correct = 0

    rows = []

    for message, expected in TEST_CASES:

        keyword_elapsed, keyword_result, keyword_error = measure(
            keyword_route_request,
            message,
        )

        ai_elapsed, ai_result, ai_error = measure(
            ai_classify_route,
            message,
        )

        if keyword_error is None:
            keyword_times.append(keyword_elapsed)

            if keyword_result == expected:
                keyword_correct += 1

        if ai_error is None:
            ai_times.append(ai_elapsed)

            if ai_result == expected:
                ai_correct += 1

        rows.append(
            {
                "message": message,
                "expected": expected,
                "keyword_result": keyword_result,
                "keyword_time": keyword_elapsed,
                "ai_result": ai_result,
                "ai_time": ai_elapsed,
            }
        )

        print(
            f"\nREQUEST: {message!r}  (expected={expected})"
        )

        print(
            f"  Keyword: {keyword_result!r:12} "
            f"{keyword_elapsed:.4f}s"
        )

        print(
            f"  AI     : {ai_result!r:12} "
            f"{ai_elapsed:.4f}s"
        )

    # =====================================================
    # Summary
    # =====================================================

    total = len(TEST_CASES)

    print("\n\n")
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print(
        f"Accuracy   - Keyword: {keyword_correct}/{total}   "
        f"AI: {ai_correct}/{total}"
    )

    if keyword_times:
        print(
            f"Latency    - Keyword: avg={mean(keyword_times):.4f}s "
            f"median={median(keyword_times):.4f}s"
        )

    if ai_times:
        print(
            f"Latency    - AI:      avg={mean(ai_times):.4f}s "
            f"median={median(ai_times):.4f}s"
        )

    # =====================================================
    # Detailed table
    # =====================================================

    print("\n")
    print("=" * 100)
    print("DETAILED RESULTS")
    print("=" * 100)

    print(
        f"{'Request':45} "
        f"{'Expected':10} "
        f"{'Keyword':10} "
        f"{'AI':10}"
    )

    print("-" * 100)

    for row in rows:

        keyword_mark = (
            "OK" if row["keyword_result"] == row["expected"] else "XX"
        )

        ai_mark = (
            "OK" if row["ai_result"] == row["expected"] else "XX"
        )

        print(
            f"{row['message'][:45]:45} "
            f"{row['expected']:10} "
            f"{str(row['keyword_result']):8} {keyword_mark} "
            f"{str(row['ai_result']):8} {ai_mark}"
        )

    print("=" * 100)


if __name__ == "__main__":
    main()
