import csv
import requests
import time


API_URL = "http://localhost:8000/api/v1/ask/ablation/context-selection"


QUESTIONS = [
    # Simple
    ("Q01", "simple", "What is a database?"),
    ("Q02", "simple", "What is supervised learning?"),
    ("Q03", "simple", "What is a neural network?"),
    ("Q04", "simple", "What is an operating system?"),
    ("Q05", "simple", "What is SQL?"),
    ("Q06", "simple", "What is classification?"),
    ("Q07", "simple", "What is regression?"),
    ("Q08", "simple", "What is gradient descent?"),
    ("Q09", "simple", "What is exploratory data analysis?"),
    ("Q10", "simple", "What is hypothesis testing?"),

    # Complex
    ("Q11", "complex", "Explain how supervised learning works."),
    ("Q12", "complex", "Why is exploratory data analysis performed in a data analytics project?"),
    ("Q13", "complex", "Explain how a neural network learns."),
    ("Q14", "complex", "What are the main responsibilities of an operating system?"),
    ("Q15", "complex", "Explain the role of SQL in database systems."),
    ("Q16", "complex", "What is supervised learning and what are its main types?"),
    ("Q17", "complex", "Explain the main components of a neural network."),
    ("Q18", "complex", "Why are labels important in supervised learning?"),
    ("Q19", "complex", "Explain the five steps of hypothesis testing."),
    ("Q20", "complex", "Why is data analysis important in a data analytics project?"),

    # Multi-concept / multi-chunk
    ("Q21", "multi_chunk", "What is supervised learning and how is it different from a neural network?"),
    ("Q22", "multi_chunk", "What are the responsibilities of an operating system and how do they help applications?"),
    ("Q23", "multi_chunk", "Explain classification and regression in supervised learning."),
    ("Q24", "multi_chunk", "What are the input, hidden, and output layers of a neural network?"),
    ("Q25", "multi_chunk", "How do gradient descent and backpropagation help neural networks learn?"),
    ("Q26", "multi_chunk", "What is a database system and what role does SQL play in it?"),
    ("Q27", "multi_chunk", "What is exploratory data analysis and how does it relate to descriptive statistics?"),
    ("Q28", "multi_chunk", "What are the main phases of a data analytics project lifecycle?"),
    ("Q29", "multi_chunk", "How are qualitative and quantitative analysis used in data analytics?"),
    ("Q30", "multi_chunk", "What is hypothesis testing and where does it fit in the data analytics lifecycle?"),

    # Paraphrased
    ("Q31", "paraphrased", "How does a machine learning system learn from examples that already have labels?"),
    ("Q32", "paraphrased", "Can you describe what a neural network consists of?"),
    ("Q33", "paraphrased", "What does an operating system actually do for a computer?"),
    ("Q34", "paraphrased", "What is the purpose of examining data before performing further analysis?"),
    ("Q35", "paraphrased", "How would you describe a relational database and its query language?"),

    # Out of scope
    ("Q36", "out_of_scope", "What is Kubernetes and how does it manage containers?"),
    ("Q37", "out_of_scope", "What is Docker and how does containerization work?"),
    ("Q38", "out_of_scope", "What is reinforcement learning?"),
    ("Q39", "out_of_scope", "Explain the transformer architecture used in modern large language models."),
    ("Q40", "out_of_scope", "What is Apache Spark and how does distributed processing work?"),
]


OUTPUT_FILE = "benchmark_ablation_context_selection_results.csv"


def run_question(question):
    start = time.perf_counter()

    response = requests.post(
        API_URL,
        json={
            "question": question,
            "top_k": 5,
        },
        timeout=180,
    )

    latency = time.perf_counter() - start
    response.raise_for_status()

    data = response.json()

    return data, latency


rows = []

for question_id, category, question in QUESTIONS:
    print(f"\n[{question_id}] {question}")

    try:
        data, client_latency = run_question(question)

        rows.append({
            "question_id": question_id,
            "category": category,
            "question": question,
            "system_type": "ablation_context_selection",
            "answer": data.get("answer", ""),
            "strategy": data.get("retrieval_method", ""),
            "context_count": data.get("selected_context_count", 0),
            "prompt_tokens": data.get("prompt_tokens", 0),
            "completion_tokens": data.get("completion_tokens", 0),
            "total_tokens": data.get("total_tokens", 0),
            "total_latency_seconds": data.get("latency", {}).get(
                "total_seconds",
                client_latency,
            ),
            "answerable": category != "out_of_scope",
        })

        print(
            f"  strategy={data.get('retrieval_method')}, "
            f"context={data.get('selected_context_count')}, "
            f"tokens={data.get('total_tokens')}, "
            f"time={data.get('latency', {}).get('total_seconds'):.2f}s"
        )

    except Exception as e:
        print(f"  ERROR: {e}")

        rows.append({
            "question_id": question_id,
            "category": category,
            "question": question,
            "system_type": "ablation_context_selection",
            "answer": f"ERROR: {e}",
            "strategy": "",
            "context_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "total_latency_seconds": 0,
            "answerable": category != "out_of_scope",
        })


with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "question_id",
            "category",
            "question",
            "system_type",
            "answer",
            "strategy",
            "context_count",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "total_latency_seconds",
            "answerable",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


answerable_rows = [
    r for r in rows
    if r["answerable"] and not r["answer"].startswith("ERROR:")
]

successful_rows = [
    r for r in rows
    if not r["answer"].startswith("ERROR:")
]


def average(rows, field):
    if not rows:
        return 0

    return sum(float(r[field]) for r in rows) / len(rows)


print("\n==============================")
print("ADAPTIVE RETRIEVAL ABLATION")
print("==============================")

print(f"Questions completed: {len(successful_rows)}/{len(rows)}")

print(
    f"Average prompt tokens: "
    f"{average(successful_rows, 'prompt_tokens'):.2f}"
)

print(
    f"Average completion tokens: "
    f"{average(successful_rows, 'completion_tokens'):.2f}"
)

print(
    f"Average total tokens: "
    f"{average(successful_rows, 'total_tokens'):.2f}"
)

print(
    f"Average context chunks: "
    f"{average(successful_rows, 'context_count'):.2f}"
)

print(
    f"Average latency: "
    f"{average(successful_rows, 'total_latency_seconds'):.2f}s"
)

print(
    f"Answerable questions: "
    f"{len(answerable_rows)}"
)

print(f"\nResults saved to: {OUTPUT_FILE}")
