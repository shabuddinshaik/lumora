import csv
import os
import time
import requests

BASE_URL = os.getenv("LUMORA_API", "http://localhost:8000")

QUESTIONS = [
    # ============================================================
    # SIMPLE — 20
    # ============================================================

    {"id":"Q01","category":"simple","question":"What is a database?","expected_facts":"A database is a structured system for storing, organizing, retrieving, and managing data.","answerable":"yes"},
    {"id":"Q02","category":"simple","question":"What is supervised learning?","expected_facts":"Supervised learning uses labeled training data with known targets or labels.","answerable":"yes"},
    {"id":"Q03","category":"simple","question":"What is a neural network?","expected_facts":"A neural network is a machine learning model with input, hidden, and output layers.","answerable":"yes"},
    {"id":"Q04","category":"simple","question":"What is an operating system?","expected_facts":"An operating system manages computer resources and provides services for applications.","answerable":"yes"},
    {"id":"Q05","category":"simple","question":"What is SQL?","expected_facts":"SQL is used to work with relational databases and data stored in tables.","answerable":"yes"},
    {"id":"Q06","category":"simple","question":"What are the main types of supervised learning?","expected_facts":"The main types are classification and regression.","answerable":"yes"},
    {"id":"Q07","category":"simple","question":"What is exploratory data analysis?","expected_facts":"EDA helps understand data and identify patterns, gaps, and insights.","answerable":"yes"},
    {"id":"Q08","category":"simple","question":"What is hypothesis testing?","expected_facts":"Hypothesis testing is a structured process used to validate a hypothesis.","answerable":"yes"},
    {"id":"Q09","category":"simple","question":"What is NPV?","expected_facts":"NPV is a financial analysis measure used when evaluating costs and benefits over time.","answerable":"yes"},
    {"id":"Q10","category":"simple","question":"What is a stakeholder?","expected_facts":"Stakeholders are people or groups involved in or affected by a project.","answerable":"yes"},

    {"id":"Q41","category":"simple","question":"What is classification in machine learning?","expected_facts":"Classification predicts discrete categories or class labels.","answerable":"yes"},
    {"id":"Q42","category":"simple","question":"What is regression in machine learning?","expected_facts":"Regression predicts continuous numerical values.","answerable":"yes"},
    {"id":"Q43","category":"simple","question":"What is gradient descent?","expected_facts":"Gradient descent is an optimization method used to adjust model parameters during learning.","answerable":"yes"},
    {"id":"Q44","category":"simple","question":"What is a relational database?","expected_facts":"A relational database organizes data using tables and supports relationships between data.","answerable":"yes"},
    {"id":"Q45","category":"simple","question":"What is a DBMS?","expected_facts":"A DBMS is software that manages databases and provides ways to store and access data.","answerable":"yes"},
    {"id":"Q46","category":"simple","question":"What is data preparation?","expected_facts":"Data preparation cleans and structures data for further analysis.","answerable":"yes"},
    {"id":"Q47","category":"simple","question":"What is qualitative analysis?","expected_facts":"Qualitative analysis is an analysis approach used in the data analytics process.","answerable":"yes"},
    {"id":"Q48","category":"simple","question":"What is quantitative analysis?","expected_facts":"Quantitative analysis is an analysis approach used in the data analytics process.","answerable":"yes"},
    {"id":"Q49","category":"simple","question":"What is a project report?","expected_facts":"A project report compiles and communicates the findings of a project.","answerable":"yes"},
    {"id":"Q50","category":"simple","question":"What is data analysis?","expected_facts":"Data analysis examines data to identify useful information, patterns, and insights.","answerable":"yes"},

    # ============================================================
    # COMPLEX — 20
    # ============================================================

    {"id":"Q11","category":"complex","question":"What are the main responsibilities of an operating system, and what are some examples?","expected_facts":"Responsibilities include process, memory, file, device, and security management. Examples include Linux, Windows, and macOS.","answerable":"yes"},
    {"id":"Q12","category":"complex","question":"What is supervised learning and how do classification and regression differ?","expected_facts":"Supervised learning uses labeled data. Classification predicts categories while regression predicts continuous values.","answerable":"yes"},
    {"id":"Q13","category":"complex","question":"How does a neural network learn?","expected_facts":"A neural network adjusts weights during training using optimization methods such as gradient descent and backpropagation.","answerable":"yes"},
    {"id":"Q14","category":"complex","question":"What are the layers of a neural network and what is the purpose of the layers?","expected_facts":"A neural network has input, hidden, and output layers that process information and produce outputs.","answerable":"yes"},
    {"id":"Q15","category":"complex","question":"What is a DBMS and how does a relational database organize data?","expected_facts":"A DBMS manages databases. Relational databases organize data using tables and support SQL.","answerable":"yes"},
    {"id":"Q16","category":"complex","question":"Why is exploratory data analysis performed in a data analytics project?","expected_facts":"EDA helps understand data, identify gaps, detect patterns, and guide further analysis.","answerable":"yes"},
    {"id":"Q17","category":"complex","question":"What are the steps involved in hypothesis testing?","expected_facts":"The corpus describes a five-step hypothesis-testing process used to validate a hypothesis.","answerable":"yes"},
    {"id":"Q18","category":"complex","question":"What are the main phases of a data analytics project lifecycle?","expected_facts":"The lifecycle contains six phases covering business problem understanding, data work, preparation, EDA and hypothesis formulation, testing, and reporting.","answerable":"yes"},
    {"id":"Q19","category":"complex","question":"What is the purpose of a project report in a data analytics project?","expected_facts":"The project report compiles findings and presents project results.","answerable":"yes"},
    {"id":"Q20","category":"complex","question":"What factors and benefits are considered when selecting data analysis tools?","expected_facts":"The corpus discusses factors related to selecting data analysis tools and their benefits.","answerable":"yes"},

    {"id":"Q51","category":"complex","question":"How does backpropagation work with gradient descent when training a neural network?","expected_facts":"Backpropagation helps calculate adjustments to weights and gradient descent is used to update them during learning.","answerable":"yes"},
    {"id":"Q52","category":"complex","question":"How does SQL help users work with data in relational databases?","expected_facts":"SQL is used to work with data stored in relational database tables.","answerable":"yes"},
    {"id":"Q53","category":"complex","question":"Why are labels important in supervised learning?","expected_facts":"Labels provide known target values that supervised learning uses during training.","answerable":"yes"},
    {"id":"Q54","category":"complex","question":"How does an operating system manage computer resources?","expected_facts":"The operating system manages resources including processes, memory, files, and devices.","answerable":"yes"},
    {"id":"Q55","category":"complex","question":"Why is data preparation performed before analysis?","expected_facts":"Data preparation cleans and structures data so it can be analyzed effectively.","answerable":"yes"},
    {"id":"Q56","category":"complex","question":"How do descriptive statistics support exploratory data analysis?","expected_facts":"Descriptive statistics help summarize and understand data during EDA.","answerable":"yes"},
    {"id":"Q57","category":"complex","question":"How does hypothesis formulation connect to later testing?","expected_facts":"A hypothesis is formulated and an appropriate testing strategy is subsequently designed to evaluate it.","answerable":"yes"},
    {"id":"Q58","category":"complex","question":"What happens during the reporting and presentation phase of a data analytics project?","expected_facts":"Findings are compiled into a report and presented.","answerable":"yes"},
    {"id":"Q59","category":"complex","question":"Why is understanding the business problem important in data analytics?","expected_facts":"The lifecycle begins with understanding the business problem before proceeding through data analysis.","answerable":"yes"},
    {"id":"Q60","category":"complex","question":"How do data analysis tools support a data analytics project?","expected_facts":"Data analysis tools provide capabilities for analyzing data and offer benefits considered during tool selection.","answerable":"yes"},

    # ============================================================
    # MULTI-CONCEPT — 20
    # ============================================================

    {"id":"Q21","category":"multi_concept","question":"Explain supervised learning and describe its two main types.","expected_facts":"Supervised learning uses labeled data. Classification predicts categories and regression predicts continuous values.","answerable":"yes"},
    {"id":"Q22","category":"multi_concept","question":"Explain neural networks and the training methods used to adjust their weights.","expected_facts":"Neural networks contain input, hidden, and output layers. Training adjusts weights using gradient descent and backpropagation.","answerable":"yes"},
    {"id":"Q23","category":"multi_concept","question":"Explain how a database and SQL are related.","expected_facts":"Relational databases organize information in tables, and SQL is used to work with relational database data.","answerable":"yes"},
    {"id":"Q24","category":"multi_concept","question":"Explain the role of an operating system in managing computer resources.","expected_facts":"The operating system manages processes, memory, files, devices, and security.","answerable":"yes"},
    {"id":"Q25","category":"multi_concept","question":"Explain why EDA is important before further data analysis.","expected_facts":"EDA helps understand data, identify gaps, detect patterns, and formulate useful questions or hypotheses.","answerable":"yes"},
    {"id":"Q26","category":"multi_concept","question":"Describe the complete six-phase data analytics project lifecycle.","expected_facts":"The six phases cover business problem understanding, data identification/acquisition/analysis, preparation, EDA and hypothesis formulation, testing, and reporting/presentation.","answerable":"yes"},
    {"id":"Q27","category":"multi_concept","question":"How are qualitative and quantitative analysis different?","expected_facts":"The corpus distinguishes qualitative and quantitative analysis as analysis approaches in data analytics.","answerable":"yes"},
    {"id":"Q28","category":"multi_concept","question":"What is the relationship between hypothesis formulation and hypothesis testing?","expected_facts":"Hypotheses are formulated and a testing strategy is subsequently designed to validate them.","answerable":"yes"},
    {"id":"Q29","category":"multi_concept","question":"How do business problems, data analysis, and project reporting fit into a data analytics project?","expected_facts":"The lifecycle starts with the business problem, proceeds through data work and analysis, and ends with reporting and presentation.","answerable":"yes"},
    {"id":"Q30","category":"multi_concept","question":"Explain how data preparation and exploratory data analysis contribute to a data analytics project.","expected_facts":"Preparation cleans and structures data while EDA helps understand it, identify patterns and gaps, and guide analysis.","answerable":"yes"},

    {"id":"Q61","category":"multi_concept","question":"Compare classification and regression and explain when each predicts categories or numerical values.","expected_facts":"Both are supervised learning tasks; classification predicts discrete categories and regression predicts continuous numerical values.","answerable":"yes"},
    {"id":"Q62","category":"multi_concept","question":"Explain the relationship between input, hidden, and output layers in a neural network.","expected_facts":"Input, hidden, and output layers process information through the network to produce an output.","answerable":"yes"},
    {"id":"Q63","category":"multi_concept","question":"Explain how a DBMS, relational tables, and SQL work together.","expected_facts":"A DBMS manages databases, relational tables organize data, and SQL is used to work with the data.","answerable":"yes"},
    {"id":"Q64","category":"multi_concept","question":"Explain how data preparation and descriptive analysis support EDA.","expected_facts":"Preparation cleans and structures data, while descriptive analysis helps summarize and understand it during EDA.","answerable":"yes"},
    {"id":"Q65","category":"multi_concept","question":"Explain the connection between labels, classification, and regression in supervised learning.","expected_facts":"Supervised learning uses labeled data; classification predicts categories and regression predicts continuous values.","answerable":"yes"},
    {"id":"Q66","category":"multi_concept","question":"Explain how gradient descent and backpropagation work together during neural network training.","expected_facts":"Backpropagation determines weight-related adjustments and gradient descent updates weights during training.","answerable":"yes"},
    {"id":"Q67","category":"multi_concept","question":"Explain how the business problem influences later data analysis and reporting.","expected_facts":"The analytics lifecycle starts by understanding the business problem and proceeds through analysis before reporting findings.","answerable":"yes"},
    {"id":"Q68","category":"multi_concept","question":"Explain why hypothesis formulation occurs before a testing strategy is applied.","expected_facts":"A hypothesis is formulated and an appropriate testing strategy is subsequently designed to evaluate it.","answerable":"yes"},
    {"id":"Q69","category":"multi_concept","question":"Explain how operating-system resource management supports applications.","expected_facts":"The operating system manages computer resources and provides services that support applications.","answerable":"yes"},
    {"id":"Q70","category":"multi_concept","question":"Explain how the main phases of a data analytics lifecycle connect from problem understanding to reporting.","expected_facts":"The lifecycle progresses from business problem understanding through data work, preparation, EDA/hypothesis formulation, testing, and reporting.","answerable":"yes"},

    # ============================================================
    # PARAPHRASED — 20
    # ============================================================

    {"id":"Q31","category":"paraphrased","question":"In simple terms, where does supervised machine learning get the correct answers used during training?","expected_facts":"It learns from labeled training examples containing known targets or labels.","answerable":"yes"},
    {"id":"Q32","category":"paraphrased","question":"What kind of structure does a relational database use to keep information organized?","expected_facts":"It organizes information using tables.","answerable":"yes"},
    {"id":"Q33","category":"paraphrased","question":"What happens to the weights inside a neural network while it is being trained?","expected_facts":"Weights are adjusted during training using methods such as gradient descent and backpropagation.","answerable":"yes"},
    {"id":"Q34","category":"paraphrased","question":"What is the main reason analysts first explore a dataset before deeper analysis?","expected_facts":"EDA helps analysts understand data, identify patterns and gaps, and guide further analysis.","answerable":"yes"},
    {"id":"Q35","category":"paraphrased","question":"At the end of an analytics project, what is done with the findings?","expected_facts":"The project report is compiled and findings are presented.","answerable":"yes"},

    {"id":"Q71","category":"paraphrased","question":"Where do the target answers come from when a supervised learning model is trained?","expected_facts":"They come from labeled training examples with known targets.","answerable":"yes"},
    {"id":"Q72","category":"paraphrased","question":"How are records arranged in a relational database?","expected_facts":"Relational databases organize information using tables.","answerable":"yes"},
    {"id":"Q73","category":"paraphrased","question":"How are neural-network weights changed as the model learns?","expected_facts":"Weights are adjusted during training using gradient descent and backpropagation.","answerable":"yes"},
    {"id":"Q74","category":"paraphrased","question":"Why do analysts examine their data before doing the main analysis?","expected_facts":"EDA helps understand data, identify gaps and patterns, and guide further analysis.","answerable":"yes"},
    {"id":"Q75","category":"paraphrased","question":"What happens to the conclusions at the close of an analytics project?","expected_facts":"Findings are compiled into a report and presented.","answerable":"yes"},
    {"id":"Q76","category":"paraphrased","question":"What does a learning algorithm use as the known target during supervised training?","expected_facts":"It uses labels or known target values in the training examples.","answerable":"yes"},
    {"id":"Q77","category":"paraphrased","question":"What structure lets a relational database store information in an organized way?","expected_facts":"It uses tables to organize information.","answerable":"yes"},
    {"id":"Q78","category":"paraphrased","question":"What is adjusted inside a neural network during training?","expected_facts":"The network weights are adjusted during training.","answerable":"yes"},
    {"id":"Q79","category":"paraphrased","question":"What is the purpose of looking at a dataset before applying deeper analytical methods?","expected_facts":"EDA helps understand the dataset and identify patterns, gaps, and useful questions.","answerable":"yes"},
    {"id":"Q80","category":"paraphrased","question":"How are project results communicated after the analytics work is completed?","expected_facts":"The findings are compiled in a project report and presented.","answerable":"yes"},
    {"id":"Q81","category":"paraphrased","question":"What information tells a supervised model what the correct prediction should be?","expected_facts":"Known labels or target values provide the correct answers during training.","answerable":"yes"},
    {"id":"Q82","category":"paraphrased","question":"How does a relational system arrange its stored information?","expected_facts":"It arranges information in tables.","answerable":"yes"},
    {"id":"Q83","category":"paraphrased","question":"During neural-network learning, what model parameters are updated?","expected_facts":"The network weights are updated during training.","answerable":"yes"},
    {"id":"Q84","category":"paraphrased","question":"Why would an analyst investigate a dataset before moving to advanced analysis?","expected_facts":"EDA provides understanding of data, patterns, gaps, and insights for further analysis.","answerable":"yes"},
    {"id":"Q85","category":"paraphrased","question":"How are the final findings shared with stakeholders after an analytics project?","expected_facts":"The findings are compiled into a report and presented.","answerable":"yes"},

    # ============================================================
    # OUT-OF-SCOPE — 20
    # ============================================================

    {"id":"Q36","category":"out_of_scope","question":"What is Kubernetes and how does it manage containers?","expected_facts":"The available learning corpus does not contain enough information about Kubernetes.","answerable":"no"},
    {"id":"Q37","category":"out_of_scope","question":"What is Docker and how does Docker Compose work?","expected_facts":"The available learning corpus does not contain enough information about Docker or Docker Compose.","answerable":"no"},
    {"id":"Q38","category":"out_of_scope","question":"What is Amazon Web Services and what is EC2?","expected_facts":"The available learning corpus does not contain enough information about AWS or EC2.","answerable":"no"},
    {"id":"Q39","category":"out_of_scope","question":"What is Retrieval-Augmented Generation?","expected_facts":"The available learning corpus does not contain enough information about RAG.","answerable":"no"},
    {"id":"Q40","category":"out_of_scope","question":"How does an LLM generate text?","expected_facts":"The available learning corpus does not contain enough information about large language models or text generation.","answerable":"no"},

    {"id":"Q86","category":"out_of_scope","question":"What is blockchain and how does it work?","expected_facts":"The available learning corpus does not contain enough information about blockchain.","answerable":"no"},
    {"id":"Q87","category":"out_of_scope","question":"What is quantum computing?","expected_facts":"The available learning corpus does not contain enough information about quantum computing.","answerable":"no"},
    {"id":"Q88","category":"out_of_scope","question":"What is computer vision?","expected_facts":"The available learning corpus does not contain enough information about computer vision.","answerable":"no"},
    {"id":"Q89","category":"out_of_scope","question":"What is natural language processing?","expected_facts":"The available learning corpus does not contain enough information about natural language processing.","answerable":"no"},
    {"id":"Q90","category":"out_of_scope","question":"What is cybersecurity and how does it protect systems?","expected_facts":"The available learning corpus does not contain enough information about cybersecurity.","answerable":"no"},
    {"id":"Q91","category":"out_of_scope","question":"What is cryptocurrency and how does Bitcoin work?","expected_facts":"The available learning corpus does not contain enough information about cryptocurrency or Bitcoin.","answerable":"no"},
    {"id":"Q92","category":"out_of_scope","question":"What is Kubernetes orchestration used for?","expected_facts":"The available learning corpus does not contain enough information about Kubernetes orchestration.","answerable":"no"},
    {"id":"Q93","category":"out_of_scope","question":"What is Apache Spark and how does distributed processing work?","expected_facts":"The available learning corpus does not contain enough information about Apache Spark.","answerable":"no"},
    {"id":"Q94","category":"out_of_scope","question":"What is reinforcement learning?","expected_facts":"The available learning corpus does not contain enough information about reinforcement learning.","answerable":"no"},
    {"id":"Q95","category":"out_of_scope","question":"What is a transformer architecture in modern AI models?","expected_facts":"The available learning corpus does not contain enough information about transformer architecture.","answerable":"no"},
    {"id":"Q96","category":"out_of_scope","question":"How does an API gateway work?","expected_facts":"The available learning corpus does not contain enough information about API gateways.","answerable":"no"},
    {"id":"Q97","category":"out_of_scope","question":"What is container orchestration?","expected_facts":"The available learning corpus does not contain enough information about container orchestration.","answerable":"no"},
    {"id":"Q98","category":"out_of_scope","question":"What is cloud computing?","expected_facts":"The available learning corpus does not contain enough information about cloud computing.","answerable":"no"},
    {"id":"Q99","category":"out_of_scope","question":"What is a convolutional neural network?","expected_facts":"The available learning corpus does not contain enough information about convolutional neural networks.","answerable":"no"},
    {"id":"Q100","category":"out_of_scope","question":"What is federated learning?","expected_facts":"The available learning corpus does not contain enough information about federated learning.","answerable":"no"},
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

    return response.json(), elapsed


def main():
    results = []
    evaluation_key = []

    print("=" * 70)
    print("LUMORA 100-QUESTION FINAL VALIDATION BENCHMARK")
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

        # Agentic / Full Lumora
        print("Running Full Lumora...")

        try:
            agentic, agentic_wall_time = ask(
                "/api/v1/ask",
                question,
            )

            agentic_answer = agentic.get(
                "response",
                agentic.get("answer", ""),
            )
            agentic_tokens = agentic.get("total_tokens", 0)
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
            print(f"Full Lumora ERROR: {e}")
            agentic_answer = ""
            agentic_tokens = 0
            agentic_context = 0
            agentic_strategy = ""
            agentic_latency = 0

        # Fixed RAG
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
            fixed_tokens = fixed.get("total_tokens", 0)
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
            print(f"Fixed RAG ERROR: {e}")
            fixed_answer = ""
            fixed_tokens = 0
            fixed_context = 0
            fixed_strategy = "fixed"
            fixed_latency = 0

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

        evaluation_key.append({
            "question_id": question_id,
            "category": item["category"],
            "question": question,
            "expected_facts": item["expected_facts"],
            "answerable": item["answerable"],
        })

        print(f"Full Lumora tokens : {agentic_tokens}")
        print(f"Full Lumora context: {agentic_context}")
        print(f"Full Lumora time   : {agentic_latency:.2f}s")
        print(f"Fixed tokens       : {fixed_tokens}")
        print(f"Fixed context      : {fixed_context}")
        print(f"Fixed time         : {fixed_latency:.2f}s")
        print()

    with open(
        "benchmark_100_results.csv",
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
        "evaluation_key_100.csv",
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

    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

    for system in ["agentic_rag", "fixed_rag"]:
        data = [
            r for r in results
            if r["system_type"] == system
        ]

        avg_tokens = sum(
            float(r["total_tokens"]) for r in data
        ) / len(data)

        avg_context = sum(
            float(r["context_count"]) for r in data
        ) / len(data)

        avg_latency = sum(
            float(r["total_latency_seconds"]) for r in data
        ) / len(data)

        print()
        print(system)
        print(f"Average tokens : {avg_tokens:.2f}")
        print(f"Average context: {avg_context:.2f}")
        print(f"Average latency: {avg_latency:.2f}s")

    agentic = [
        r for r in results
        if r["system_type"] == "agentic_rag"
    ]

    fixed = [
        r for r in results
        if r["system_type"] == "fixed_rag"
    ]

    agentic_tokens = sum(
        float(r["total_tokens"]) for r in agentic
    ) / len(agentic)

    fixed_tokens = sum(
        float(r["total_tokens"]) for r in fixed
    ) / len(fixed)

    reduction = (
        (fixed_tokens - agentic_tokens)
        / fixed_tokens
    ) * 100

    print()
    print(f"Average token reduction: {reduction:.2f}%")
    print()
    print("Created:")
    print("  benchmark_100_results.csv")
    print("  evaluation_key_100.csv")


if __name__ == "__main__":
    main()
