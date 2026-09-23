import time

from memory_retrieval import get_compact_memory
from session_memory import get_recent_memory


conversation_id = 48


print("=" * 70)
print("MEMORY BENCHMARK")
print("=" * 70)


# ---------------------------------------------------------
# Raw memory
# ---------------------------------------------------------

start = time.perf_counter()

raw_memory = get_recent_memory(
    conversation_id,
    max_interactions=3,
)

raw_time = time.perf_counter() - start


print("\n[RAW MEMORY]")
print("-" * 70)
print(raw_memory)
print(f"\nCharacters: {len(raw_memory)}")
print(f"Retrieval time: {raw_time * 1000:.2f} ms")


# ---------------------------------------------------------
# Compact memory
# ---------------------------------------------------------

start = time.perf_counter()

compact_memory = get_compact_memory(
    conversation_id,
    max_interactions=3,
)

compact_time = time.perf_counter() - start


print("\n[COMPACT MEMORY]")
print("-" * 70)
print(compact_memory)
print(f"\nCharacters: {len(compact_memory)}")
print(f"Retrieval time: {compact_time * 1000:.2f} ms")


# ---------------------------------------------------------
# Comparison
# ---------------------------------------------------------

if raw_memory:
    reduction = (
        1 - (len(compact_memory) / len(raw_memory))
    ) * 100
else:
    reduction = 0


print("\n" + "=" * 70)
print("COMPARISON")
print("=" * 70)

print(f"Raw characters:      {len(raw_memory)}")
print(f"Compact characters:  {len(compact_memory)}")
print(f"Character reduction: {reduction:.2f}%")

print(f"\nRaw retrieval:       {raw_time * 1000:.2f} ms")
print(f"Compact retrieval:   {compact_time * 1000:.2f} ms")
