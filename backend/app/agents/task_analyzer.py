from dataclasses import dataclass


@dataclass
class TaskAnalysis:
    task_type: str
    complexity: str
    requires_context: bool
    requires_retrieval: bool
    requires_validation: bool

    # All-rounder task metadata.
    artifact_type: str = "natural_language"
    language: str | None = None


def detect_artifact(query: str) -> tuple[str, str | None]:
    """
    Detect the expected output artifact and language.

    This is deterministic and intentionally conservative.
    It does not decide whether retrieval is required.
    """

    text = query.strip().lower()

    # ---------------------------------------------------------
    # Configuration / infrastructure artifacts
    # ---------------------------------------------------------

    if any(term in text for term in [
        "docker compose",
        "docker-compose",
        "compose.yaml",
        "compose.yml",
    ]):
        return "docker_compose", "yaml"

    if any(term in text for term in [
        "kubernetes deployment",
        "kubernetes service",
        "kubernetes configmap",
        "kubernetes ingress",
        "kubernetes manifest",
        "k8s deployment",
        "k8s service",
        "k8s manifest",
    ]):
        return "kubernetes_manifest", "yaml"

    if any(term in text for term in [
        "terraform",
        "terraform configuration",
        "terraform module",
    ]):
        return "terraform", "hcl"

    # ---------------------------------------------------------
    # SQL
    # ---------------------------------------------------------

    if any(term in text for term in [
        "sql query",
        "write sql",
        "write a sql",
        "postgresql query",
        "mysql query",
        "database query",
        "select query",
    ]):
        return "sql_query", "sql"

    # ---------------------------------------------------------
    # Shell
    # ---------------------------------------------------------

    if any(term in text for term in [
        "bash script",
        "bash command",
        "shell script",
        "shell command",
        "linux command",
        "shell",
    ]):
        return "shell_script", "bash"

    # ---------------------------------------------------------
    # Python
    # ---------------------------------------------------------

    if any(term in text for term in [
        "python",
        "pytest",
        "pandas",
        "numpy",
        "fastapi",
        "flask",
    ]):
        return "source_code", "python"

    # ---------------------------------------------------------
    # JavaScript / TypeScript
    # ---------------------------------------------------------

    if any(term in text for term in [
        "javascript",
        "js code",
        "node.js",
        "nodejs",
        "typescript",
        "typescript code",
        "react component",
    ]):
        return "source_code", "javascript"

    # ---------------------------------------------------------
    # Explicit JSON
    # ---------------------------------------------------------

    if any(term in text for term in [
        "json",
        "json object",
        "json payload",
    ]):
        return "json", "json"

    # ---------------------------------------------------------
    # Generic code request
    # ---------------------------------------------------------

    if any(term in text for term in [
        "write code",
        "create code",
        "generate code",
        "write a function",
        "create a function",
        "implement a function",
        "program",
        "script",
    ]):
        return "source_code", None

    return "natural_language", None


def analyze_task(query: str) -> TaskAnalysis:
    """
    Lightweight task analysis.

    This is the first baseline implementation.
    It is intentionally deterministic and does not call an LLM.
    """

    text = query.strip().lower()

    artifact_type, language = detect_artifact(query)

    if not text:
        return TaskAnalysis(
            task_type="general",
            complexity="simple",
            requires_context=False,
            requires_retrieval=False,
            requires_validation=False,
        )

    # ---------------------------------------------------------
    # 1. Identify the requested operation first.
    # ---------------------------------------------------------

    if any(term in text for term in [
        "summarize",
        "summary",
        "summarise",
    ]):
        task_type = "summarization"

    elif any(term in text for term in [
        "compare",
        "comparison",
        "difference",
        "differences",
        "versus",
        " vs ",
    ]):
        task_type = "comparison"

    elif any(term in text for term in [
        "analyze",
        "analyse",
        "dataset",
        "data analysis",
        "statistics",
        "standard deviation",
        "variance",
        "correlation",
        "anomaly",
        "outlier",
    ]) and not any(term in text for term in [
        "create a python",
        "create python",
        "write a python",
        "write python",
        "python function",
        "python code",
        "generate python",
        "implement a python",
    ]):
        task_type = "data_analysis"

    elif any(term in text for term in [
        "debug",
        "debugging",
        "crash",
        "crashing",
        "error",
        "exception",
        "failure",
        "failing",
        "not working",
        "doesn't work",
        "does not work",
    ]):
        task_type = "debugging"

    else:
        # ---------------------------------------------------------
        # Developer / engineering task classification
        # ---------------------------------------------------------

        # Testing requests
        if any(term in text for term in [
            "test",
            "tests",
            "testing",
            "pytest",
            "unit test",
            "unit tests",
            "test cases",
        ]) and any(term in text for term in [
            "code",
            "function",
            "python",
            "javascript",
            "class",
            "program",
        ]):
            task_type = "testing"

        # Refactoring requests
        elif any(term in text for term in [
            "refactor",
            "refactoring",
            "clean up",
            "clean-up",
            "improve the structure",
        ]):
            task_type = "refactoring"

        # SQL generation
        elif artifact_type == "sql_query":
            task_type = "sql_generation"

        # Infrastructure/configuration generation
        elif artifact_type in {
            "docker_compose",
            "kubernetes_manifest",
            "terraform",
            "json",
        }:
            task_type = "configuration_generation"

        # Shell / DevOps tasks
        elif artifact_type == "shell_script":
            task_type = "devops_task"

        # Source-code generation/modification
        elif artifact_type == "source_code":
            modification_terms = [
                "modify",
                "fix",
                "change",
                "update",
                "add",
                "remove",
                "correct",
                "rewrite",
            ]

            if any(term in text for term in modification_terms):
                task_type = "code_modification"
            else:
                task_type = "code_generation"

        # Data analysis
        elif any(term in text for term in [
            "analyze",
            "analyse",
            "dataset",
            "data analysis",
            "statistics",
            "standard deviation",
            "variance",
            "correlation",
            "anomaly",
            "outlier",
        ]):
            task_type = "data_analysis"

        # General information
        elif any(term in text for term in [
            "explain",
            "what is",
            "what are",
            "tell me about",
            "why",
            "how",
            "define",
            "definition",
        ]):
            task_type = "information"

        else:
            task_type = "general"

    # ---------------------------------------------------------
    # 2. Estimate task complexity.
    # ---------------------------------------------------------

    complex_terms = [
        " and ",
        "compare",
        "comparison",
        "multiple",
        "all ",
        "steps",
        "requirements",
        "implement",
        "refactor",
        "debug",
        "analyze",
        "analyse",
    ]

    complexity = (
        "complex"
        if any(term in text for term in complex_terms)
        else "simple"
    )

    # ---------------------------------------------------------
    # 3. Determine context and retrieval requirements.
    # ---------------------------------------------------------

    # Explicit signals that the user wants information from a
    # provided/known knowledge source.
    retrieval_signals = [
        "uploaded",
        "document",
        "pdf",
        "notes",
        "from my notes",
        "from the document",
        "from the pdf",
        "from this file",
        "based on the document",
        "based on the file",
        "based on my notes",
        "according to the document",
        "according to the file",
        "according to my notes",
        "use the document",
        "use this file",
        "use my notes",
        "knowledge base",
        "knowledgebase",
        "my data",
        "this data",
        "provided context",
        "provided code",
        "code above",
        "code below",
        "pasted code",
    ]

    explicit_retrieval_request = any(
        signal in text
        for signal in retrieval_signals
    )

    # Context means that the task depends on material supplied by
    # the user. Generation by itself does not require context.
    code_modification_signals = [
        "fix this",
        "fix the",
        "debug this",
        "debug the",
        "modify this",
        "modify the",
        "change this",
        "change the",
        "refactor this",
        "refactor the",
        "update this",
        "update the",
        "rewrite this",
        "rewrite the",
    ]

    has_supplied_code_context = (
        any(signal in text for signal in code_modification_signals)
        or any(signal in text for signal in [
            "provided code",
            "code above",
            "code below",
            "pasted code",
        ])
    )

    requires_context = False
    requires_retrieval = False

    # Source-based tasks need context and retrieval.
    if task_type in {"summarization", "comparison"}:
        requires_context = True
        requires_retrieval = explicit_retrieval_request

    # Explicitly supplied code/data is context, but does not require
    # knowledge-base retrieval unless the user asks for it.
    elif task_type in {"code_modification", "debugging"}:
        requires_context = has_supplied_code_context
        requires_retrieval = explicit_retrieval_request

    elif task_type == "data_analysis":
        requires_context = (
            explicit_retrieval_request
            or "dataset" in text
            or "data" in text
        )
        requires_retrieval = explicit_retrieval_request

    elif task_type == "information":
        requires_context = explicit_retrieval_request
        requires_retrieval = explicit_retrieval_request

    elif task_type == "general":
        requires_context = explicit_retrieval_request
        requires_retrieval = explicit_retrieval_request

    # Pure generation tasks do not need external context.
    elif task_type in {
        "code",
        "code_generation",
        "sql_generation",
        "configuration_generation",
        "devops_task",
        "testing",
        "refactoring",
    }:
        requires_context = has_supplied_code_context
        requires_retrieval = explicit_retrieval_request

    # Retrieval is never implied merely because a task produces code.
    if explicit_retrieval_request:
        requires_retrieval = True

    # ---------------------------------------------------------
    # 4. Validation.
    # ---------------------------------------------------------

    requires_validation = task_type in {
        "code_modification",
        "code_generation",
        "code",
        "debugging",
        "testing",
        "refactoring",
        "sql_generation",
        "configuration_generation",
        "devops_task",
        "data_analysis",
        "comparison",
        "summarization",
    }

    return TaskAnalysis(
        task_type=task_type,
        complexity=complexity,
        requires_context=requires_context,
        requires_retrieval=requires_retrieval,
        requires_validation=requires_validation,
        artifact_type=artifact_type,
        language=language,
    )
