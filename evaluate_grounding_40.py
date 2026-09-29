import csv
import re

RESULTS_FILE = "benchmark_40_results.csv"
KEY_FILE = "evaluation_key_40.csv"
OUTPUT_FILE = "grounding_refusal_40.csv"


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def answer_refuses(answer):
    """
    Detect whether the answer explicitly indicates that
    the required information is unavailable from the corpus.
    """

    text = normalize(answer)

    refusal_patterns = [
        "not available",
        "not provided",
        "not mentioned",
        "not covered",
        "not included",
        "not present",
        "outside the provided",
        "outside the supplied",
        "does not contain",
        "cannot answer",
        "cannot be answered",
        "insufficient information",
        "information is insufficient",
        "not enough information",
        "not in the provided",
        "not in the supplied",
        "not found in the provided",
        "not found in the supplied",
        "the documents do not",
        "the document does not",
        "the corpus does not",
        "knowledge corpus does not",
    ]

    return any(pattern in text for pattern in refusal_patterns)


def calculate_keyword_coverage(answer, expected):

    answer_text = normalize(answer)
    expected_text = normalize(expected)

    expected_words = set(expected_text.split())

    # Ignore very common words.
    stopwords = {
        "the", "a", "an", "and", "or", "is", "are",
        "was", "were", "of", "to", "in", "for",
        "on", "with", "what", "how", "why", "when",
        "where", "which", "that", "this", "some",
        "main", "examples", "following", "include"
    }

    meaningful_words = {
        word
        for word in expected_words
        if len(word) >= 4 and word not in stopwords
    }

    if not meaningful_words:
        return 1.0

    answer_words = set(answer_text.split())

    matched = meaningful_words.intersection(answer_words)

    return len(matched) / len(meaningful_words)


def main():

    results = load_csv(RESULTS_FILE)
    key = load_csv(KEY_FILE)

    key_map = {
        row["question_id"]: row
        for row in key
    }

    output = []

    for row in results:

        qid = row["question_id"]
        system = row["system_type"]

        key_row = key_map[qid]

        answerable = key_row["answerable"]
        answer = row["answer"]
        expected = key_row["expected_facts"]

        if answerable == "no":

            refused = answer_refuses(answer)

            # Deterministic refusal score
            refusal_score = 2 if refused else 0

            # If the system refuses, it does not introduce
            # unsupported knowledge.
            grounding_score = 2 if refused else 0

            coverage = ""

        else:

            refused = False
            refusal_score = ""

            coverage = calculate_keyword_coverage(
                answer,
                expected
            )

            # This is only a diagnostic grounding indicator.
            #
            # >= 0.50 means the answer contains substantial
            # overlap with the expected corpus information.
            if coverage >= 0.50:
                grounding_score = 2
            elif coverage >= 0.25:
                grounding_score = 1
            else:
                grounding_score = 0

        output.append({
            "question_id": qid,
            "system_type": system,
            "answerable": answerable,
            "refused": refused,
            "refusal_score": refusal_score,
            "grounding_score": grounding_score,
            "keyword_coverage": coverage,
        })


    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question_id",
                "system_type",
                "answerable",
                "refused",
                "refusal_score",
                "grounding_score",
                "keyword_coverage",
            ],
        )

        writer.writeheader()
        writer.writerows(output)


    print("=" * 70)
    print("GROUNDING / REFUSAL EVALUATION")
    print("=" * 70)

    for system in ["agentic_rag", "fixed_rag"]:

        rows = [
            r for r in output
            if r["system_type"] == system
        ]

        answerable_rows = [
            r for r in rows
            if r["answerable"] == "yes"
        ]

        oos_rows = [
            r for r in rows
            if r["answerable"] == "no"
        ]

        grounding_values = [
            float(r["grounding_score"])
            for r in answerable_rows
        ]

        refusal_values = [
            float(r["refusal_score"])
            for r in oos_rows
        ]

        grounding_avg = (
            sum(grounding_values) / len(grounding_values)
            if grounding_values else 0
        )

        refusal_avg = (
            sum(refusal_values) / len(refusal_values)
            if refusal_values else 0
        )

        refusal_rate = (
            sum(
                1
                for r in oos_rows
                if r["refused"]
            )
            / len(oos_rows)
            * 100
            if oos_rows else 0
        )

        print()
        print(system)

        print(
            f"Grounding (answerable): "
            f"{grounding_avg:.2f}/2"
        )

        print(
            f"Appropriate refusal: "
            f"{refusal_avg:.2f}/2"
        )

        print(
            f"Refusal rate: "
            f"{refusal_rate:.1f}%"
        )


    print()
    print(f"Created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
