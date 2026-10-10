import csv
import os
import requests

from benchmark_40 import QUESTIONS


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

ENDPOINTS = {
    "controlled_fixed_rag": "/api/v1/ask/ablation/fixed-rag",
    "controlled_adaptive_retrieval": "/api/v1/ask/ablation/adaptive-retrieval",
    "controlled_full_lumora": "/api/v1/ask/ablation/full-lumora",
}


def ask(endpoint, question):
    response = requests.post(
        BASE_URL + endpoint,
        json={
            "question": question,
            "top_k": 5,
            "task_type": "auto",
        },
        timeout=180,
    )

    response.raise_for_status()
    return response.json()


def extract_result(system_type, question_id, question, data):
    latency = data.get("latency", {})

    strategy = (
        data.get("final_strategy")
        or data.get("selected_strategy")
        or data.get("retrieval_method")
        or ""
    )

    context_count = (
        data.get("selected_context_count")
        if data.get("selected_context_count") is not None
        else data.get("result_count", 0)
    )

    answer = data.get("answer", "")

    refusal_phrases = [
        "not enough information",
        "do not contain enough information",
        "insufficient information",
        "cannot answer",
        "unable to answer",
    ]

    outcome = (
        "refused"
        if any(phrase in answer.lower() for phrase in refusal_phrases)
        else "answered"
    )

    return {
        "system": system_type,
        "question_id": question_id,
        "question": question,
        "answer": answer,
        "outcome": outcome,
        "strategy": strategy,
        "context_count": context_count,
        "total_tokens": data.get("total_tokens", 0),
        "latency_seconds": latency.get("total_seconds", 0),
    }


def main():
    results = []

    print("=" * 80)
    print("CONTROLLED 40-QUESTION BENCHMARK")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Questions: {len(QUESTIONS)}")
    print()

    for index, item in enumerate(QUESTIONS, start=1):
        question_id = item["id"]
        question = item["question"]

        print(f"[{question_id}] {question}")

        for system_type, endpoint in ENDPOINTS.items():
            try:
                data = ask(endpoint, question)
                row = extract_result(
                    system_type,
                    question_id,
                    question,
                    data,
                )
                results.append(row)

                print(
                    f"  {system_type}: "
                    f"{row['total_tokens']} tokens, "
                    f"{row['context_count']} chunks, "
                    f"{row['latency_seconds']:.2f}s"
                )

            except Exception as exc:
                print(f"  {system_type}: ERROR - {exc}")

                results.append(
                    {
                        "system": system_type,
                        "question_id": question_id,
                        "question": question,
                        "answer": "",
                        "outcome": "error",
                        "strategy": "",
                        "context_count": 0,
                        "total_tokens": 0,
                        "latency_seconds": 0,
                    }
                )

        print()

    results_file = "benchmark_controlled_40_results.csv"

    with open(results_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "system",
                "question_id",
                "question",
                "answer",
                "outcome",
                "strategy",
                "context_count",
                "total_tokens",
                "latency_seconds",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print("=" * 80)
    print("AVERAGES")
    print("=" * 80)

    for system_type in ENDPOINTS:
        system_results = [
            r for r in results
            if r["system"] == system_type
            and r["answer"]
        ]

        if not system_results:
            print(f"{system_type}: no successful results")
            continue

        avg_tokens = sum(
            r["total_tokens"] for r in system_results
        ) / len(system_results)

        avg_context = sum(
            r["context_count"] for r in system_results
        ) / len(system_results)

        avg_latency = sum(
            r["latency_seconds"] for r in system_results
        ) / len(system_results)

        print(f"\n{system_type}")
        print(f"  Questions:       {len(system_results)}")
        print(f"  Avg tokens:      {avg_tokens:.2f}")
        print(f"  Avg chunks:      {avg_context:.2f}")
        print(f"  Avg latency:     {avg_latency:.2f}s")

    print()
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    main()
