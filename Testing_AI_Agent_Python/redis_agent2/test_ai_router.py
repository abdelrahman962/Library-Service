"""
Live test for the AI router.

Runs classify_route() against real phrasings - including ones that
don't contain the old keyword router's literal keywords - and prints
expected vs. actual for each case. This hits Ollama for real (same as
test_memory.py / test_recent_memory.py do for the Laravel API), so it
is a manual/integration check, not a mocked unit test.
"""

from ai_router import classify_route


# ---------------------------------------------------------
# Test cases: (message, expected_route)
#
# The second block deliberately avoids the old keyword router's
# trigger words (e.g. "book", "borrow", "my profile") - these are
# the cases keyword matching couldn't handle but semantic
# classification should.
# ---------------------------------------------------------

TEST_CASES = [

    # -------------------------------------------------
    # Straightforward phrasing
    # -------------------------------------------------

    ("search for Python books", "books"),
    ("show details about Sapiens", "books"),
    ("what is my email?", "user"),
    ("what information do you have about me?", "user"),
    ("borrow Clean Code", "borrowing"),
    ("return Sapiens", "borrowing"),
    ("show library statistics", "admin"),
    ("show Omar's borrowing history", "admin"),

    # -------------------------------------------------
    # No literal keyword overlap with the old router
    # -------------------------------------------------

    ("Which titles can I take home right now?", "books"),
    ("I'm looking for something to learn Python", "books"),
    ("Could you show me everything in the catalog?", "books"),
    ("Can you tell me what's on my account?", "user"),
    ("I finished reading Clean Code and want to give it back.", "borrowing"),
    ("Can I take this one home with me?", "borrowing"),
    ("Who else has an account here?", "admin"),
]


def main():

    print("=== AI Router Test ===\n")

    passed = 0
    failed = 0

    for message, expected in TEST_CASES:

        actual = classify_route(message)

        ok = actual == expected

        status = "PASS" if ok else "FAIL"

        if ok:
            passed += 1
        else:
            failed += 1

        print(
            f"[{status}] {message!r}\n"
            f"       expected={expected!r} actual={actual!r}"
        )

    total = passed + failed

    print(
        f"\n=== {passed}/{total} passed "
        f"({failed} failed) ==="
    )


if __name__ == "__main__":
    main()
