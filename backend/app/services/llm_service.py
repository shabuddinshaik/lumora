import requests


OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "qwen3:1.7b"


def _generate(
    prompt: str,
    num_predict: int,
) -> dict:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": num_predict,
            },
        },
        timeout=600,
    )

    response.raise_for_status()

    data = response.json()

    return {
        "response": data.get("response", "").strip(),
        "prompt_tokens": data.get("prompt_eval_count", 0),
        "completion_tokens": data.get("eval_count", 0),
        "total_tokens": (
            data.get("prompt_eval_count", 0)
            + data.get("eval_count", 0)
        ),
    }


def generate_answer(prompt: str) -> dict:
    result = _generate(
        prompt,
        num_predict=512,
    )

    return result

def validate_task_satisfaction(
    question: str,
    answer: str,
    task_type: str,
) -> dict:
    prompt = f"""You are a strict task-completion evaluator for Lumora.

Evaluate whether the Answer actually satisfies the User Request.

Task Type:
{task_type}

User Request:
{question}

Answer:
{answer}

Rules:
1. Judge whether the answer actually performs what the user requested.
2. Do not judge style or writing quality.
3. For code modification or debugging, check that the proposed code
   actually fixes the reported problem without changing the intended
   behavior unnecessarily.
4. Do not accept an answer merely because it avoids a technical error.
5. If the answer changes the requested computation or behavior without
   justification, mark it NOT_SATISFIED.
6. If the answer is incomplete, mark it NOT_SATISFIED.
7. Use only the User Request and Answer.
8. Return exactly one of these two values:
   SATISFIED
   NOT_SATISFIED

Decision:
"""

    result = _generate(
        prompt,
        num_predict=16,
    )

    decision = result["response"].strip().upper()

    if decision.startswith("SATISFIED"):
        satisfied = True
    elif decision.startswith("NOT_SATISFIED"):
        satisfied = False
    else:
        satisfied = False

    return {
        "satisfied": satisfied,
        "decision": decision,
        "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
        "total_tokens": result["total_tokens"],
    }


def refine_answer(
    question: str,
    previous_answer: str,
    validation_message: str,
    task_type: str,
) -> dict:
    prompt = f"""You are Lumora performing a targeted correction.

The previous generated answer failed an independent validation check.

Task Type:
{task_type}

Original User Request:
{question}

Previous Answer:
{previous_answer}

Validation Error:
{validation_message}

Your job is to produce a NEW corrected answer.

STRICT RULES:
1. Treat the Original User Request as the source of truth.
2. Treat the Validation Error as a concrete defect that must be fixed.
3. Do not simply explain the previous answer.
4. Do not repeat the defective code or operation.
5. If this is a coding task, return complete corrected working code.
6. Preserve the user's intended behavior.
7. Do not introduce unrelated changes.
8. Check the new answer against the Validation Error before returning it.
9. Return only the final answer to the user.
10. Do not mention validation, retry, refinement, or these instructions.

Original User Request:
{question}

Produce the corrected answer now:
"""

    result = _generate(
        prompt,
        num_predict=512,
    )

    return result


def check_evidence_sufficiency(
    question: str,
    context: str,
) -> bool:
    if not context.strip():
        return False

    # Deterministic guard for comparison requests.
    # Each compared subject must have meaningful evidence in the context.
    comparison_terms = [
        "compare",
        "comparison",
        "difference",
        "differences",
        "versus",
        " vs ",
    ]

    question_lower = question.lower()

    if any(term in question_lower for term in comparison_terms):
        import re

        match = re.search(
            r"(?:compare|comparison|difference|differences|versus)\\s+"
            r"(.+?)(?:\\s+and\\s+|\\s+vs\\.?\\s+|\\s+versus\\s+)"
            r"(.+?)(?:\\s+and\\s+|\\s*$)",
            question_lower,
        )

        if match:
            subject_a = match.group(1).strip()
            subject_b = match.group(2).strip()

            context_lower = context.lower()

            subject_a_present = subject_a in context_lower
            subject_b_present = subject_b in context_lower

            if not subject_a_present or not subject_b_present:
                print(
                    "[Evidence Guard] comparison subjects missing: "
                    f"A={subject_a_present} B={subject_b_present}"
                )
                return False

    prompt = f"""You are an evidence verification checker for Lumora.

Your job is to decide whether the provided Context contains ALL important
evidence required to fulfill the User Request.

Use ONLY the Context.
Do NOT use your own knowledge.
Do NOT assume missing information.

The Context can contain:
- natural-language information
- source code
- configuration
- logs
- documentation
- structured data

GENERAL RULES:

1. The Context must contain the evidence needed to complete the request.
2. A topic being mentioned is NOT enough.
3. Do not fill missing information using outside knowledge.
4. If an important requested subject, component, value, or operation is missing,
   return INSUFFICIENT.
5. For multi-part requests, ALL important parts must be supported.
6. Prefer INSUFFICIENT when there is meaningful uncertainty.

FOR INFORMATION REQUESTS:

The Context must explicitly contain the information needed to answer.

Example:

User Request:
"Explain supervised learning."

Context:
"Supervised learning uses labeled training data..."

Decision:
SUFFICIENT

If the Context only says:

"Machine learning includes supervised learning."

Decision:
INSUFFICIENT

because the Context does not actually explain supervised learning.

FOR COMPARISON REQUESTS:

Identify the main subjects being compared.

The Context must contain meaningful information about EACH subject.

Example:

User Request:
"Compare supervised learning and unsupervised learning."

If Context contains:
- detailed information about supervised learning
- only a mention of unsupervised learning

Decision:
INSUFFICIENT

If Context contains meaningful information about both supervised learning
and unsupervised learning:

Decision:
SUFFICIENT

Do NOT infer missing properties of either subject from general knowledge.

FOR MULTI-PART REQUESTS:

Identify the important parts of the request.

The Context must contain enough evidence for ALL important parts.

If one important part is missing:

Decision:
INSUFFICIENT

FOR SOURCE CODE REQUESTS:

If the User Request asks to modify, explain, debug, refactor, test, or extend
code, and the Context contains the relevant source code, return SUFFICIENT.

The requested modification does NOT need to already exist in the Context.

Example:

User Request:
"Modify calculate_total() so that it raises ValueError for negative values."

Context:
"def calculate_total(items):
    total = 0
    for item in items:
        total += item["price"] * item["quantity"]
    return total"

Decision:
SUFFICIENT

Return ONLY one of:

SUFFICIENT
INSUFFICIENT

User Request:
{question}

Context:
{context}

Decision:
"""
    result = _generate(
        prompt,
        num_predict=16,
    )

    print("[Evidence Checker Raw Response]")
    print(repr(result["response"]))
    print("[End Evidence Checker Raw Response]")

    decision = result["response"].strip().upper()

    if decision.startswith("SUFFICIENT"):
        return True

    if decision.startswith("INSUFFICIENT"):
        return False

    return False
