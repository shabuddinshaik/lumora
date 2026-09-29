import requests
import csv
import time
import psycopg2

BASE_URL = "http://localhost:8000"

DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "database": "lumora",
    "user": "lumora",
    "password": "lumora_password",
}

QUESTIONS = [
    ("Q1", "simple", "What is a database?"),
    ("Q2", "multi_part", "What are the main responsibilities of an operating system, and what are some examples of operating systems?"),
    ("Q3", "simple", "What is supervised learning?"),
    ("Q4", "simple", "What is a neural network?"),
    ("Q5", "multi_part", "What is supervised learning, and what are its main types?"),
    ("Q6", "multi_part", "What are the six phases of a data analytics project lifecycle?"),
    ("Q7", "complex", "What is exploratory data analysis, and why is it performed in a data analytics project?"),
    ("Q8", "unanswerable", "What is Kubernetes and how does it manage containers?"),
]


def get_latest_run():
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    selected_strategy,
                    final_strategy,
                    fallback_count,
                    total_retrieved_count,
                    final_retrieved_count,
                    selected_context_count,
                    evidence_sufficient,
                    retrieval_latency_seconds,
                    generation_latency_seconds,
                    total_latency_seconds,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens
                FROM evaluation_runs
                ORDER BY id DESC
                LIMIT 1;
            """)

            row = cur.fetchone()

            if row is None:
                raise RuntimeError("No evaluation_run found.")

            columns = [
                "run_id",
                "selected_strategy",
                "final_strategy",
                "fallback_count",
                "total_retrieved_count",
                "final_retrieved_count",
                "selected_context_count",
                "evidence_sufficient",
                "retrieval_latency_seconds",
                "generation_latency_seconds",
                "total_latency_seconds",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
            ]

            return dict(zip(columns, row))

    finally:
        conn.close()


def run_test(endpoint, question):
    response = requests.post(
        f"{BASE_URL}{endpoint}",
        json={"question": question, "top_k": 5},
        timeout=180,
    )

    response.raise_for_status()

    return response.json()


results = []

for qid, category, question in QUESTIONS:

    print(f"\nRunning {qid}: {question}")

    for system, endpoint in [
        ("agentic_rag", "/api/v1/ask"),
        ("fixed_rag", "/api/v1/ask/fixed"),
    ]:

        print(f"  {system}...")

        try:
            before = get_latest_run()

            data = run_test(endpoint, question)

            after = get_latest_run()

            # Make sure a new evaluation run was created.
            if after["run_id"] == before["run_id"]:
                raise RuntimeError(
                    "Evaluation run ID did not change after API request."
                )

            results.append({
                "question_id": qid,
                "category": category,
                "question": question,
                "system_type": system,

                "run_id": after["run_id"],

                "selected_strategy": after["selected_strategy"],
                "final_strategy": after["final_strategy"],

                "fallback_count": after["fallback_count"],
                "total_retrieved_count": after["total_retrieved_count"],
                "final_retrieved_count": after["final_retrieved_count"],
                "selected_context_count": after["selected_context_count"],

                "evidence_sufficient": after["evidence_sufficient"],

                "retrieval_latency_seconds": after[
                    "retrieval_latency_seconds"
                ],
                "generation_latency_seconds": after[
                    "generation_latency_seconds"
                ],
                "total_latency_seconds": after[
                    "total_latency_seconds"
                ],

                "prompt_tokens": after["prompt_tokens"],
                "completion_tokens": after["completion_tokens"],
                "total_tokens": after["total_tokens"],

                "answer": data.get("answer", ""),
            })

        except Exception as e:
            print(f"  ERROR: {e}")


if not results:
    raise RuntimeError("No benchmark results were collected.")


output_file = "benchmark_results.csv"

fieldnames = [
    "question_id",
    "category",
    "question",
    "system_type",
    "run_id",
    "selected_strategy",
    "final_strategy",
    "fallback_count",
    "total_retrieved_count",
    "final_retrieved_count",
    "selected_context_count",
    "evidence_sufficient",
    "retrieval_latency_seconds",
    "generation_latency_seconds",
    "total_latency_seconds",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "answer",
]


with open(output_file, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(results)


print("\nBenchmark completed.")
print(f"Results saved to: {output_file}")
print(f"Total benchmark records: {len(results)}")
