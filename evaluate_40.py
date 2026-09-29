import csv
import json
import requests
import statistics

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:1.7b"

RESULTS_FILE = "benchmark_40_results.csv"
KEY_FILE = "evaluation_key_40.csv"
OUTPUT_FILE = "quality_evaluation_40.csv"


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def judge(question, answer, expected_facts, answerable):

    if answerable == "no":
        rubric = """
This is an OUT-OF-SCOPE question.

Evaluate ONLY:

refusal:
2 = clearly refuses because the required information is not available
    in the supplied knowledge corpus.
1 = recognizes the limitation but also gives some unsupported information.
0 = answers the question using outside knowledge.

grounding:
2 = does not introduce unsupported factual information.
1 = contains a small amount of unsupported information.
0 = substantially provides information outside the supplied corpus.

For an out-of-scope question:
correctness = null
completeness = null
"""

    else:
        rubric = """
This is an ANSWERABLE question.

Evaluate:

correctness:
2 = factually correct.
1 = partially correct or has a minor factual issue.
0 = substantially incorrect.

completeness:
2 = covers the important expected facts.
1 = misses some important expected information.
0 = substantially incomplete.

grounding:
2 = answer is supported by the supplied expected information.
1 = mostly supported but contains a minor unsupported addition.
0 = substantially unsupported.

refusal:
0 = normal answer; no refusal is needed.
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
- Do not use outside knowledge.
- Do not reward unnecessary verbosity.
- For out-of-scope questions, correctness and completeness MUST be null.
- Return ONLY valid JSON.

Use exactly this structure:

{{
  "correctness": null,
  "completeness": null,
  "grounding": 0,
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
                "num_predict": 200,
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
            "grounding": 0,
            "refusal": 0,
            "comment": "Judge response could not be parsed.",
        }


def safe_score(value):
    if value is None:
        return None

    try:
        return float(value)
    except:
        return None


def average(rows, field):

    values = []

    for row in rows:
        value = safe_score(row[field])

        if value is not None:
            values.append(value)

    if not values:
        return None

    return statistics.mean(values)


def main():

    results = load_csv(RESULTS_FILE)
    key = load_csv(KEY_FILE)

    key_map = {
        row["question_id"]: row
        for row in key
    }

    evaluations = []

    print("=" * 70)
    print("LUMORA 40-QUESTION QUALITY EVALUATION")
    print("=" * 70)

    for i, row in enumerate(results, 1):

        qid = row["question_id"]
        system = row["system_type"]

        expected = key_map[qid]

        print(
            f"[{i}/{len(results)}] "
            f"{qid} - {system}"
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
            "system_type": system,
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
            "grounding": evaluation.get("grounding"),
            "refusal": (
                None
                if is_answerable
                else evaluation.get("refusal")
            ),
            "comment": evaluation.get("comment", ""),
        })


    # ------------------------------------------------------------
    # Save detailed evaluation
    # ------------------------------------------------------------

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
                "grounding",
                "refusal",
                "comment",
            ],
        )

        writer.writeheader()
        writer.writerows(evaluations)


    # ------------------------------------------------------------
    # Separate answerable / out-of-scope evaluations
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("QUALITY EVALUATION COMPLETE")
    print("=" * 70)

    for system in ["agentic_rag", "fixed_rag"]:

        system_rows = [
            r for r in evaluations
            if r["system_type"] == system
        ]

        answerable_rows = [
            r for r in system_rows
            if r["answerable"] == "yes"
        ]

        out_of_scope_rows = [
            r for r in system_rows
            if r["answerable"] == "no"
        ]

        correctness = average(
            answerable_rows,
            "correctness",
        )

        completeness = average(
            answerable_rows,
            "completeness",
        )

        grounding_answerable = average(
            answerable_rows,
            "grounding",
        )

        grounding_oos = average(
            out_of_scope_rows,
            "grounding",
        )

        refusal = average(
            out_of_scope_rows,
            "refusal",
        )

        print()
        print(system)

        print(
            f"Answerable questions: "
            f"{len(answerable_rows)}"
        )

        print(
            f"Out-of-scope questions: "
            f"{len(out_of_scope_rows)}"
        )

        print(
            f"Correctness : "
            f"{correctness:.2f}/2"
            if correctness is not None
            else "Correctness : N/A"
        )

        print(
            f"Completeness: "
            f"{completeness:.2f}/2"
            if completeness is not None
            else "Completeness: N/A"
        )

        print(
            f"Grounding (answerable): "
            f"{grounding_answerable:.2f}/2"
            if grounding_answerable is not None
            else "Grounding (answerable): N/A"
        )

        print(
            f"Grounding (out-of-scope): "
            f"{grounding_oos:.2f}/2"
            if grounding_oos is not None
            else "Grounding (out-of-scope): N/A"
        )

        print(
            f"Appropriate refusal: "
            f"{refusal:.2f}/2"
            if refusal is not None
            else "Appropriate refusal: N/A"
        )


    print()
    print(f"Created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
