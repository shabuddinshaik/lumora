import re


def _clean_subject(subject: str) -> str:
    subject = subject.strip().lower()

    subject = re.sub(
        r"\b(and explain|and describe|and discuss|and tell me)\b.*$",
        "",
        subject,
    )

    subject = re.sub(
        r"\b(their main differences|their differences|main differences|differences)\b.*$",
        "",
        subject,
    )

    return subject.strip(" .,:;?")


def _has_meaningful_evidence(subject: str, context: str) -> bool:
    """
    Determine whether the context contains meaningful information about
    the requested subject, rather than merely mentioning the subject.
    """
    subject = _clean_subject(subject)
    context_lower = context.lower()

    if not subject:
        return False

    occurrences = [
        match.start()
        for match in re.finditer(
            re.escape(subject),
            context_lower,
        )
    ]

    if not occurrences:
        return False

    # Multiple occurrences are a useful signal that the subject is actually
    # discussed rather than merely listed once.
    if len(occurrences) >= 2:
        return True

    position = occurrences[0]

    # Only inspect text immediately around this subject.
    start = max(0, position - 120)
    end = min(
        len(context_lower),
        position + len(subject) + 180,
    )

    surrounding = context_lower[start:end]

    # A single occurrence inside a list/category statement is not enough.
    weak_patterns = [
        r"divided into[^.]*\b" + re.escape(subject) + r"\b",
        r"includes[^.]*\b" + re.escape(subject) + r"\b",
        r"include[^.]*\b" + re.escape(subject) + r"\b",
        r"such as[^.]*\b" + re.escape(subject) + r"\b",
        r"types of[^.]*\b" + re.escape(subject) + r"\b",
        r"types include[^.]*\b" + re.escape(subject) + r"\b",
        r"methods[^.]*\b" + re.escape(subject) + r"\b",
        r"approaches[^.]*\b" + re.escape(subject) + r"\b",
    ]

    for pattern in weak_patterns:
        if re.search(pattern, surrounding):
            return False

    # For a single occurrence, require an explanatory statement that is
    # directly associated with the subject.
    subject_pattern = re.escape(subject)

    strong_patterns = [
        rf"{subject_pattern}\s+(?:uses|is|are|refers to|means|involves)",
        rf"{subject_pattern}[^.]*\buses\b",
        rf"{subject_pattern}[^.]*\btraining data\b",
        rf"{subject_pattern}[^.]*\bdata\b",
        rf"{subject_pattern}[^.]*\bmodel\b",
        rf"{subject_pattern}[^.]*\bgoal\b",
        rf"{subject_pattern}[^.]*\baim\b",
        rf"{subject_pattern}[^.]*\bidentif",
        rf"{subject_pattern}[^.]*\bpredict",
        rf"{subject_pattern}[^.]*\bcluster",
    ]

    for pattern in strong_patterns:
        if re.search(pattern, surrounding):
            return True

    return False


def validate_comparison_evidence(
    question: str,
    context: str,
) -> bool:
    """
    Validate that both subjects in a comparison have meaningful evidence.
    """
    if not context.strip():
        return False

    question_lower = question.lower()

    match = re.search(
        r"compare\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)(?:\s+and\s+|\s*$)",
        question_lower,
    )

    if not match:
        return True

    subject_a = _clean_subject(match.group(1))
    subject_b = _clean_subject(match.group(2))

    evidence_a = _has_meaningful_evidence(
        subject_a,
        context,
    )

    evidence_b = _has_meaningful_evidence(
        subject_b,
        context,
    )

    print(
        "[Comparison Evidence] "
        f"subject_a='{subject_a}' supported={evidence_a} "
        f"subject_b='{subject_b}' supported={evidence_b}"
    )

    return evidence_a and evidence_b


def validate_evidence(
    question: str,
    context: str,
    task_type: str,
) -> bool:
    """
    Deterministic evidence validation before the LLM evidence checker.
    """
    if not context.strip():
        return False

    if task_type == "comparison":
        return validate_comparison_evidence(
            question,
            context,
        )

    return True
