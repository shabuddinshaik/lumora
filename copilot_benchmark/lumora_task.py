import requests
import time

LUMORA_URL = "http://localhost/api/v1/ask"

question = """Modify the project so that calculate_total() treats a missing
"quantity" key as quantity 1 while preserving the existing behavior when
"quantity" is present.

Update the existing pytest test file to add tests covering:
1. An item without "quantity" is treated as quantity 1.
2. An item with an explicit quantity continues to work normally.

Do not remove or modify the existing test.

Return the complete modified code for both affected files."""

start = time.perf_counter()

response = requests.post(
    LUMORA_URL,
    json={
        "question": question,
        "top_k": 5,
        "document_id": 19,
        "task_type": "auto",
    },
    timeout=600,
)

response.raise_for_status()

elapsed = time.perf_counter() - start
data = response.json()

print("=" * 70)
print("LUMORA CODING TEST")
print("=" * 70)
print(f"Prompt tokens     : {data.get('prompt_tokens', 0)}")
print(f"Completion tokens : {data.get('completion_tokens', 0)}")
print(f"Total tokens      : {data.get('total_tokens', 0)}")
print(f"Latency           : {elapsed:.2f}s")
print(f"Strategy          : {data.get('final_strategy')}")
print(f"Context chunks    : {data.get('selected_context_count')}")

print("\nANSWER:")
print(data.get("answer", ""))
