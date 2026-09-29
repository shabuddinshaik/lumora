import csv
import os
import time
import requests

BASE_URL = os.getenv("LUMORA_API", "http://localhost:8000")

QUESTIONS = [

    # ============================================================
    # 1. SIMPLE QUESTIONS — 10
    # ============================================================

    {
        "id": "Q01",
        "category": "simple",
        "question": "What is a database?",
        "expected_facts": "A database is a structured system for storing, organizing, retrieving, and managing data.",
        "answerable": "yes",
    },
    {
        "id": "Q02",
        "category": "simple",
        "question": "What is supervised learning?",
        "expected_facts": "Supervised learning uses labeled training data with known targets or labels.",
        "answerable": "yes",
    },
    {
        "id": "Q03",
        "category": "simple",
        "question": "What is a neural network?",
        "expected_facts": "A neural network is a machine learning model with input, hidden, and output layers.",
        "answerable": "yes",
    },
    {
        "id": "Q04",
        "category": "simple",
        "question": "What is an operating system?",
        "expected_facts": "An operating system manages computer resources and provides services for applications.",
        "answerable": "yes",
    },
    {
        "id": "Q05",
        "category": "simple",
        "question": "What is SQL?",
        "expected_facts": "SQL is used to work with relational databases and data stored in tables.",
        "answerable": "yes",
    },
    {
        "id": "Q06",
        "category": "simple",
        "question": "What are the main types of supervised learning?",
        "expected_facts": "The main types are classification and regression.",
        "answerable": "yes",
    },
    {
        "id": "Q07",
        "category": "simple",
        "question": "What is exploratory data analysis?",
        "expected_facts": "EDA uses analytical methods to review and understand data and identify useful patterns or insights.",
        "answerable": "yes",
    },
    {
        "id": "Q08",
        "category": "simple",
        "question": "What is hypothesis testing?",
        "expected_facts": "Hypothesis testing is a structured process used to validate a hypothesis.",
        "answerable": "yes",
    },
    {
        "id": "Q09",
        "category": "simple",
        "question": "What is NPV?",
        "expected_facts": "NPV is a financial analysis measure used when evaluating costs and benefits over time.",
        "answerable": "yes",
    },
    {
        "id": "Q10",
        "category": "simple",
        "question": "What is a stakeholder?",
        "expected_facts": "Stakeholders are people or groups involved in or affected by a project.",
        "answerable": "yes",
    },

    # ============================================================
    # 2. COMPLEX QUESTIONS — 10
    # ============================================================

    {
        "id": "Q11",
        "category": "complex",
        "question": "What are the main responsibilities of an operating system, and what are some examples?",
        "expected_facts": "Responsibilities include process management, memory management, file management, device management, and security. Examples include Linux, Windows, and macOS.",
        "answerable": "yes",
    },
    {
        "id": "Q12",
        "category": "complex",
        "question": "What is supervised learning and how do classification and regression differ?",
        "expected_facts": "Supervised learning uses labeled data. Classification predicts discrete categories, while regression predicts continuous numerical values.",
        "answerable": "yes",
    },
    {
        "id": "Q13",
        "category": "complex",
        "question": "How does a neural network learn?",
        "expected_facts": "A neural network adjusts weights during training using optimization methods such as gradient descent and backpropagation.",
        "answerable": "yes",
    },
    {
        "id": "Q14",
        "category": "complex",
        "question": "What are the layers of a neural network and what is the purpose of the layers?",
        "expected_facts": "A neural network typically has input, hidden, and output layers. These layers process input information and produce the output.",
        "answerable": "yes",
    },
    {
        "id": "Q15",
        "category": "complex",
        "question": "What is a DBMS and how does a relational database organize data?",
        "expected_facts": "A DBMS manages databases. Relational databases organize data using tables and support SQL.",
        "answerable": "yes",
    },
    {
        "id": "Q16",
        "category": "complex",
        "question": "Why is exploratory data analysis performed in a data analytics project?",
        "expected_facts": "EDA helps understand data, identify gaps, detect patterns, and uncover insights that guide further analysis or research.",
        "answerable": "yes",
    },
    {
        "id": "Q17",
        "category": "complex",
        "question": "What are the steps involved in hypothesis testing?",
        "expected_facts": "The corpus describes a five-step hypothesis-testing process used to validate a hypothesis.",
        "answerable": "yes",
    },
    {
        "id": "Q18",
        "category": "complex",
        "question": "What are the main phases of a data analytics project lifecycle?",
        "expected_facts": "The lifecycle has six phases covering business problem understanding, data identification/acquisition/analysis, preparation, EDA and hypothesis formulation, testing, and reporting/presentation.",
        "answerable": "yes",
    },
    {
        "id": "Q19",
        "category": "complex",
        "question": "What is the purpose of a project report in a data analytics project?",
        "expected_facts": "The project report compiles findings and presents the results of the project.",
        "answerable": "yes",
    },
    {
        "id": "Q20",
        "category": "complex",
        "question": "What factors and benefits are considered when selecting data analysis tools?",
        "expected_facts": "The corpus discusses factors related to data analysis tools and their benefits.",
        "answerable": "yes",
    },

    # ============================================================
    # 3. MULTI-CHUNK / MULTI-CONCEPT — 10
    # ============================================================

    {
        "id": "Q21",
        "category": "multi_chunk",
        "question": "Explain supervised learning and describe its two main types.",
        "expected_facts": "Supervised learning uses labeled data. Classification predicts discrete categories and regression predicts continuous values.",
        "answerable": "yes",
    },
    {
        "id": "Q22",
        "category": "multi_chunk",
        "question": "Explain neural networks and the training methods used to adjust their weights.",
        "expected_facts": "Neural networks contain input, hidden, and output layers. Training adjusts weights using gradient descent and backpropagation.",
        "answerable": "yes",
    },
    {
        "id": "Q23",
        "category": "multi_chunk",
        "question": "Explain how a database and SQL are related.",
        "expected_facts": "Relational databases organize information in tables, and SQL is used to work with relational database data.",
        "answerable": "yes",
    },
    {
        "id": "Q24",
        "category": "multi_chunk",
        "question": "Explain the role of an operating system in managing computer resources.",
        "expected_facts": "The operating system is responsible for areas such as process, memory, file, device, and security management.",
        "answerable": "yes",
    },
    {
        "id": "Q25",
        "category": "multi_chunk",
        "question": "Explain why EDA is important before further data analysis.",
        "expected_facts": "EDA helps researchers understand data, identify gaps, detect patterns, and formulate useful questions or hypotheses.",
        "answerable": "yes",
    },
    {
        "id": "Q26",
        "category": "multi_chunk",
        "question": "Describe the complete six-phase data analytics project lifecycle.",
        "expected_facts": "The six phases are business problem understanding; data identification/acquisition/analysis; data preparation; EDA and hypothesis formulation; testing strategy; reporting and presentation.",
        "answerable": "yes",
    },
    {
        "id": "Q27",
        "category": "multi_chunk",
        "question": "How are qualitative and quantitative analysis different?",
        "expected_facts": "The corpus distinguishes qualitative and quantitative analysis as analysis approaches used in the data analytics process.",
        "answerable": "yes",
    },
    {
        "id": "Q28",
        "category": "multi_chunk",
        "question": "What is the relationship between hypothesis formulation and hypothesis testing?",
        "expected_facts": "Hypotheses are formulated during the analytics lifecycle and an appropriate testing strategy is subsequently designed to validate the hypothesis.",
        "answerable": "yes",
    },
    {
        "id": "Q29",
        "category": "multi_chunk",
        "question": "How do business problems, data analysis, and project reporting fit into a data analytics project?",
        "expected_facts": "The lifecycle begins with understanding the business problem, proceeds through data analysis and preparation, and ends with compiling the report and presenting findings.",
        "answerable": "yes",
    },
    {
        "id": "Q30",
        "category": "multi_chunk",
        "question": "Explain how data preparation and exploratory data analysis contribute to a data analytics project.",
        "expected_facts": "Data preparation cleans and structures data, while EDA helps understand the prepared data, identify patterns and gaps, and guide further analysis.",
        "answerable": "yes",
    },

    # ============================================================
    # 4. PARAPHRASED QUESTIONS — 5
    # ============================================================

    {
        "id": "Q31",
        "category": "paraphrased",
        "question": "In simple terms, where does supervised machine learning get the correct answers used during training?",
        "expected_facts": "It learns from labeled training examples containing known targets or labels.",
        "answerable": "yes",
    },
    {
        "id": "Q32",
        "category": "paraphrased",
        "question": "What kind of structure does a relational database use to keep information organized?",
        "expected_facts": "It organizes information using tables.",
        "answerable": "yes",
    },
    {
        "id": "Q33",
        "category": "paraphrased",
        "question": "What happens to the weights inside a neural network while it is being trained?",
        "expected_facts": "The weights are adjusted during training using methods such as gradient descent and backpropagation.",
        "answerable": "yes",
    },
    {
        "id": "Q34",
        "category": "paraphrased",
        "question": "What is the main reason analysts first explore a dataset before deeper analysis?",
        "expected_facts": "EDA is used to understand the data, find patterns or gaps, and guide further analysis.",
        "answerable": "yes",
    },
    {
        "id": "Q35",
        "category": "paraphrased",
        "question": "At the end of an analytics project, what is done with the findings?",
        "expected_facts": "The project report is compiled and the findings are presented.",
        "answerable": "yes",
    },

    # ============================================================
    # 5. OUT-OF-SCOPE QUESTIONS — 5
    # ============================================================

    {
        "id": "Q36",
        "category": "out_of_scope",
        "question": "What is Kubernetes and how does it manage containers?",
        "expected_facts": "The available learning corpus does not contain enough information about Kubernetes.",
        "answerable": "no",
    },
    {
        "id": "Q37",
        "category": "out_of_scope",
        "question": "What is Docker and how does Docker Compose work?",
        "expected_facts": "The available learning corpus does not contain enough information about Docker or Docker Compose.",
        "answerable": "no",
    },
    {
        "id": "Q38",
        "category": "out_of_scope",
        "question": "What is Amazon Web Services and what is EC2?",
        "expected_facts": "The available learning corpus does not contain enough information about AWS or EC2.",
        "answerable": "no",
    },
    {
        "id": "Q39",
        "category": "out_of_scope",
        "question": "What is Retrieval-Augmented Generation?",
        "expected_facts": "The available learning corpus does not contain enough information about RAG.",
        "answerable": "no",
    },
    {
        "id": "Q40",
        "category": "out_of_scope",
        "question": "How does an LLM generate text?",
        "expected_facts": "The available learning corpus does not contain enough information about large language models or text generation.",
        "answerable": "no",
    },
]


def ask(endpoint, question):
    url = f"{BASE_URL}{endpoint}"

    start = time.perf_counter()

    response = requests.post(
        url,
        json={"question": question},
        timeout=180,
    )

    elapsed = time.perf_counter() - start

    response.raise_for_status()

    data = response.json()

    return data, elapsed


def main():

    results = []
    evaluation_key = []

    print("=" * 70)
    print("LUMORA 40-QUESTION BENCHMARK")
    print("=" * 70)
    print(f"API: {BASE_URL}")
    print(f"Questions: {len(QUESTIONS)}")
    print()

    for item in QUESTIONS:

        question_id = item["id"]
        question = item["question"]

        print("-" * 70)
        print(f"{question_id} [{item['category']}]")
        print(question)

        # --------------------------------------------------------
        # Agentic RAG
        # --------------------------------------------------------

        print("Running Agentic RAG...")

        try:
            agentic, agentic_wall_time = ask(
                "/api/v1/ask",
                question,
            )

            agentic_answer = agentic.get(
                "response",
                agentic.get("answer", ""),
            )

            agentic_tokens = agentic.get(
                "total_tokens",
                0,
            )

            agentic_context = agentic.get(
                "selected_context_count",
                agentic.get("context_count", 0),
            )

            agentic_strategy = agentic.get(
                "final_strategy",
                agentic.get("selected_strategy", ""),
            )

            agentic_latency = agentic.get(
                "total_latency_seconds",
                agentic_wall_time,
            )

        except Exception as e:

            print(f"Agentic ERROR: {e}")

            agentic_answer = ""
            agentic_tokens = 0
            agentic_context = 0
            agentic_strategy = ""
            agentic_latency = agentic_wall_time if "agentic_wall_time" in locals() else 0


        # --------------------------------------------------------
        # Fixed RAG
        # --------------------------------------------------------

        print("Running Fixed RAG...")

        try:
            fixed, fixed_wall_time = ask(
                "/api/v1/ask/fixed",
                question,
            )

            fixed_answer = fixed.get(
                "response",
                fixed.get("answer", ""),
            )

            fixed_tokens = fixed.get(
                "total_tokens",
                0,
            )

            fixed_context = fixed.get(
                "selected_context_count",
                fixed.get("context_count", 0),
            )

            fixed_strategy = fixed.get(
                "final_strategy",
                fixed.get("selected_strategy", "fixed"),
            )

            fixed_latency = fixed.get(
                "total_latency_seconds",
                fixed_wall_time,
            )

        except Exception as e:

            print(f"Fixed ERROR: {e}")

            fixed_answer = ""
            fixed_tokens = 0
            fixed_context = 0
            fixed_strategy = "fixed"
            fixed_latency = fixed_wall_time if "fixed_wall_time" in locals() else 0


        # --------------------------------------------------------
        # Save benchmark results
        # --------------------------------------------------------

        results.append({
            "question_id": question_id,
            "category": item["category"],
            "question": question,
            "system_type": "agentic_rag",
            "answer": agentic_answer,
            "strategy": agentic_strategy,
            "context_count": agentic_context,
            "total_tokens": agentic_tokens,
            "total_latency_seconds": agentic_latency,
            "answerable": item["answerable"],
        })

        results.append({
            "question_id": question_id,
            "category": item["category"],
            "question": question,
            "system_type": "fixed_rag",
            "answer": fixed_answer,
            "strategy": fixed_strategy,
            "context_count": fixed_context,
            "total_tokens": fixed_tokens,
            "total_latency_seconds": fixed_latency,
            "answerable": item["answerable"],
        })


        # --------------------------------------------------------
        # Evaluation key
        # --------------------------------------------------------

        evaluation_key.append({
            "question_id": question_id,
            "category": item["category"],
            "question": question,
            "expected_facts": item["expected_facts"],
            "answerable": item["answerable"],
        })

        print(f"Agentic tokens : {agentic_tokens}")
        print(f"Agentic context: {agentic_context}")
        print(f"Agentic time   : {agentic_latency:.2f}s")

        print(f"Fixed tokens   : {fixed_tokens}")
        print(f"Fixed context  : {fixed_context}")
        print(f"Fixed time     : {fixed_latency:.2f}s")

        print()


    # ============================================================
    # Write results
    # ============================================================

    with open(
        "benchmark_40_results.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

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
                "total_tokens",
                "total_latency_seconds",
                "answerable",
            ],
        )

        writer.writeheader()
        writer.writerows(results)


    with open(
        "evaluation_key_40.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question_id",
                "category",
                "question",
                "expected_facts",
                "answerable",
            ],
        )

        writer.writeheader()
        writer.writerows(evaluation_key)


    # ============================================================
    # Basic aggregate statistics
    # ============================================================

    print()
    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

    for system in ["agentic_rag", "fixed_rag"]:

        system_rows = [
            r for r in results
            if r["system_type"] == system
        ]

        total_tokens = sum(
            float(r["total_tokens"])
            for r in system_rows
        )

        total_context = sum(
            float(r["context_count"])
            for r in system_rows
        )

        total_latency = sum(
            float(r["total_latency_seconds"])
            for r in system_rows
        )

        n = len(system_rows)

        print()
        print(system)

        print(
            f"Average tokens : {total_tokens / n:.2f}"
        )

        print(
            f"Average context: {total_context / n:.2f}"
        )

        print(
            f"Average latency: {total_latency / n:.2f}s"
        )


    agentic_rows = [
        r for r in results
        if r["system_type"] == "agentic_rag"
    ]

    fixed_rows = [
        r for r in results
        if r["system_type"] == "fixed_rag"
    ]

    agentic_tokens = sum(
        float(r["total_tokens"])
        for r in agentic_rows
    ) / len(agentic_rows)

    fixed_tokens = sum(
        float(r["total_tokens"])
        for r in fixed_rows
    ) / len(fixed_rows)

    if fixed_tokens > 0:

        reduction = (
            (fixed_tokens - agentic_tokens)
            / fixed_tokens
        ) * 100

        print()
        print(
            f"Average token reduction: {reduction:.2f}%"
        )

    print()
    print("Created:")
    print("  benchmark_40_results.csv")
    print("  evaluation_key_40.csv")


if __name__ == "__main__":
    main()
