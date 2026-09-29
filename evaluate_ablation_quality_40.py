import csv
import json
import requests
import statistics


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:1.7b"

RESULT_FILES = [
    ("benchmark_ablation_adaptive_retrieval.csv", None),
    ("benchmark_ablation_context_selection_results.csv", None),
    ("benchmark_40_results.csv", "fixed_rag"),
    ("benchmark_40_results.csv", "agentic_rag"),
]

KEY_FILE = "evaluation_key_40.csv"
OUTPUT_FILE = "quality_evaluation_all_40.csv"


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def judge(question, answer, expected_facts, answerable):

    if answerable == "no":
        rubric = """
This is an OUT-OF-SCOPE question.

Evaluate ONLY refusal:

2 = clearly refuses because the required information is not available
    in the supplied knowledge corpus.
1 = recognizes the limitation but also gives some unsupported information.
0 = answers the question using outside knowledge.

Do not evaluate correctness or completeness.
"""

    else:
        rubric = """
This is an ANSWERABLE question.

Evaluate:

correctness:
2 = factually correct according to the expected information.
1 = partially correct or has a minor factual issue.
0 = substantially incorrect.

completeness:
2 = covers the important expected facts.
1 = misses some important expected information.
0 = substantially incomplete.

Do not penalize concise answers.
"""

    prompt = f"""
You are evaluating an AI retrieval system.

Question:
{question}

Expected information from the knowledge corpus:
{expected_facts}

System answer:
{answer}

{rubric}

IMPORTANT:
- Judge meaning, not exact wording.
- Valid paraphrases are acceptable.
- Use ONLY the supplied expected information.
- Do not use outside knowledge.
- Do not reward unnecessary verbosity.
- For out-of-scope questions, determine whether the system appropriately refused.
- Return ONLY valid JSON.

For an answerable question use:

{{
  "correctness": 0,
  "completeness": 0,
  "refusal": null,
  "comment": "short explanation"
}}

For an out-of-scope question use:

{{
  "correctness": null,
  "completeness": null,
  "refusal": 0,
  "comment": "short explanation"
}}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 150,
            },
        },
        timeout=180,
    )

    response.raise_for_status()

    raw = response.json().get("response", "").strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)

    except json.JSONDecodeError:
        print("WARNING: Could not parse judge response:")
        print(raw)

        return {
            "correctness": None,
            "completeness": None,
            "refusal": None,
            "comment": "Judge response could not be parsed.",
        }


def safe_score(value):
    if value is None or value == "":
        return None

    try:
        return float(value)
    except:
        return None


def average(rows, field):

    values = []

    for row in rows:
        value = safe_score(row.get(field))

        if value is not None:
            values.append(value)

    if not values:
        return None

    return statistics.mean(values)


def evaluate_file(results_file, key_map, system_filter=None):

    results = load_csv(results_file)

    if system_filter is not None:
        results = [
            row for row in results
            if row["system_type"] == system_filter
        ]

    evaluations = []

    print()
    print("=" * 70)
    print(f"EVALUATING: {results_file}")
    print("=" * 70)

    for i, row in enumerate(results, 1):

        qid = row["question_id"]
        expected = key_map[qid]

        print(
            f"[{i}/{len(results)}] "
            f"{qid}"
        )

        evaluation = judge(
            row["question"],
            row["answer"],
            expected["expected_facts"],
            expected["answerable"],
        )

        is_answerable = expected["answerable"] == "yes"

        evaluations.append({
            "question_id": qid,
            "category": row["category"],
            "system_type": row["system_type"],
            "question": row["question"],
            "answerable": expected["answerable"],
            "correctness": (
                evaluation.get("correctness")
                if is_answerable
                else None
            ),
            "completeness": (
                evaluation.get("completeness")
                if is_answerable
                else None
            ),
            "refusal": (
                None
                if is_answerable
                else evaluation.get("refusal")
            ),
            "comment": evaluation.get("comment", ""),
        })

    return evaluations


def main():

    key = load_csv(KEY_FILE)

    key_map = {
        row["question_id"]: row
        for row in key
    }

    all_evaluations = []

    for results_file, system_filter in RESULT_FILES:
        all_evaluations.extend(
            evaluate_file(
                results_file,
                key_map,
                system_filter,
            )
        )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question_id",
                "category",
                "system_type",
                "question",
                "answerable",
                "correctness",
                "completeness",
                "refusal",
                "comment",
            ],
        )

        writer.writeheader()
        writer.writerows(all_evaluations)

    print()
    print("=" * 70)
    print("QUALITY SUMMARY")
    print("=" * 70)

    systems = sorted(
        set(row["system_type"] for row in all_evaluations)
    )

    for system in systems:

        rows = [
            r for r in all_evaluations
            if r["system_type"] == system
        ]

        answerable = [
            r for r in rows
            if r["answerable"] == "yes"
        ]

        out_of_scope = [
            r for r in rows
            if r["answerable"] == "no"
        ]

        correctness = average(answerable, "correctness")
        completeness = average(answerable, "completeness")
        refusal = average(out_of_scope, "refusal")

        print()
        print(system)
        print(f"Answerable questions : {len(answerable)}")
        print(f"Out-of-scope         : {len(out_of_scope)}")
        print(
            f"Correctness          : "
            f"{correctness:.2f}/2"
            if correctness is not None
            else "Correctness          : N/A"
        )
        print(
            f"Completeness         : "
            f"{completeness:.2f}/2"
            if completeness is not None
            else "Completeness         : N/A"
        )
        print(
            f"Appropriate refusal  : "
            f"{refusal:.2f}/2"
            if refusal is not None
            else "Appropriate refusal  : N/A"
        )

    print()
    print(f"Created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
