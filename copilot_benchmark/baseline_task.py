import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:1.7b"

question = """Modify the project so that calculate_total() treats a missing
"quantity" key as quantity 1 while preserving the existing behavior when
"quantity" is present.

Update the existing pytest test file to add tests covering:
1. An item without "quantity" is treated as quantity 1.
2. An item with an explicit quantity continues to work normally.

Do not remove or modify the existing test.

Return the complete modified code for both affected files."""

context = """
File: src/calculator.py

def calculate_total(items):
    total = 0

    for item in items:
        total += item["price"] * item["quantity"]

    return total
"""

prompt = f"""You are a coding assistant.

Use the provided repository context to answer the coding task.

Repository context:
{context}

Coding task:
{question}

Provide the modified Python code for the affected function and briefly
explain the change.
"""

start = time.perf_counter()

response = requests.post(
    OLLAMA_URL,
    json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 512,
        },
    },
    timeout=600,
)

response.raise_for_status()

elapsed = time.perf_counter() - start
data = response.json()

prompt_tokens = data.get("prompt_eval_count", 0)
completion_tokens = data.get("eval_count", 0)

print("=" * 70)
print("DIRECT AI BASELINE")
print("=" * 70)
print(f"Prompt tokens     : {prompt_tokens}")
print(f"Completion tokens : {completion_tokens}")
print(f"Total tokens      : {prompt_tokens + completion_tokens}")
print(f"Latency           : {elapsed:.2f}s")

print("\nANSWER:")
print(data.get("response", ""))
