import ast
import re


def extract_python_code(answer: str) -> str | None:
    """
    Extract Python code from a markdown code block.
    If no code block exists, return None.
    """
    match = re.search(
        r"```(?:python|py)\s*(.*?)```",
        answer,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    # The model may return plain Python without a markdown code fence.
    # Only treat the answer as code when it contains strong Python signals.
    lines = answer.strip().splitlines()

    python_signals = (
        "def ",
        "import ",
        "from ",
        "print(",
        "if ",
        "for ",
        "while ",
        "return ",
        "=",
    )

    if any(
        any(line.strip().startswith(signal) for signal in python_signals)
        for line in lines
    ):
        return answer.strip()

    return None

def extract_code_block(
    answer: str,
    languages: tuple[str, ...] = (),
) -> str | None:
    """
    Extract a fenced Markdown code block.

    Supports both language-labelled and unlabelled fences.
    """
    if not answer:
        return None

    if languages:
        language_pattern = "|".join(re.escape(lang) for lang in languages)
        pattern = (
            rf"```(?:{language_pattern})[ \t]*\r?\n"
            rf"(.*?)"
            rf"\r?\n?```"
        )
    else:
        pattern = (
            r"```[^\r\n]*\r?\n"
            r"(.*?)"
            r"\r?\n?```"
        )

    match = re.search(
        pattern,
        answer,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return None

def extract_artifact(
    answer: str,
    artifact_type: str,
    language: str | None,
) -> str | None:
    """
    Extract generated content according to the expected artifact.
    """
    if not answer:
        return None

    if language == "python":
        return extract_python_code(answer)

    if language == "sql":
        return extract_code_block(answer, ("sql",)) or answer.strip()

    if language == "yaml":
        return (
            extract_code_block(answer, ("yaml", "yml"))
            or extract_code_block(answer)
            or answer.strip()
        )

    if language == "bash":
        return (
            extract_code_block(answer, ("bash", "sh", "shell"))
            or answer.strip()
        )

    if language == "json":
        return (
            extract_code_block(answer, ("json",))
            or answer.strip()
        )

    return extract_code_block(answer) or answer.strip()


def extract_arithmetic_operations(code: str) -> list[str]:
    """
    Extract normalized arithmetic operations from Python code.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    operations = []

    operator_map = {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.Div: "/",
        ast.FloorDiv: "//",
        ast.Mod: "%",
        ast.Pow: "**",
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue

        operator = operator_map.get(type(node.op))
        if operator is None:
            continue

        left = ast.unparse(node.left)
        right = ast.unparse(node.right)

        operations.append(f"{left} {operator} {right}")

    return operations


def validate_python_syntax(code: str) -> tuple[bool, str]:
    """
    Validate Python syntax without executing the code.
    """
    try:
        ast.parse(code)
        return True, "Python syntax is valid."
    except SyntaxError as exc:
        return False, f"Python syntax error: {exc}"



def deterministic_code_fix(
    code: str,
    validation_message: str,
    question: str = "",
) -> str | None:
    """
    Apply safe deterministic fixes for known static validation errors.

    Currently handles literal division, floor-division, and modulo by zero
    by removing the invalid arithmetic operation while preserving the
    left-hand expression.
    """
    if not code:
        return None

    if "division by zero" not in validation_message.lower():
        return None

    # Do not apply a generic rewrite when the user's request explicitly
    # specifies the desired error-handling behavior. In those cases the
    # LLM must interpret and implement the requested behavior.
    question_lower = question.lower()

    explicit_behavior_signals = (
        "return 0",
        "return none",
        "return null",
        "raise ",
        "throw ",
        "try/except",
        "try except",
        "handle the error",
        "handle division by zero",
        "when division by zero",
        "if division by zero",
        "error message",
        "show an error",
    )

    # Explicit request: return 0 when division by zero occurs.
    # Handle this deterministically because the desired behavior is explicit.
    if (
        (
            "return 0" in question_lower
            or "returns 0" in question_lower
            or "return zero" in question_lower
            or "returns zero" in question_lower
        )
        and (
            "division by zero" in question_lower
            or "divide by zero" in question_lower
        )
    ):
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None

        changed = False

        class ReturnZeroOnDivisionByZeroFixer(ast.NodeTransformer):
            def visit_BinOp(self, node):
                nonlocal changed

                self.generic_visit(node)

                is_zero = (
                    isinstance(node.right, ast.Constant)
                    and node.right.value == 0
                )

                is_division = isinstance(
                    node.op,
                    (ast.Div, ast.FloorDiv),
                )

                if is_zero and is_division:
                    changed = True
                    return ast.Constant(value=0)

                return node

        tree = ReturnZeroOnDivisionByZeroFixer().visit(tree)
        ast.fix_missing_locations(tree)

        if changed:
            try:
                return ast.unparse(tree)
            except Exception:
                return None

        return None

    # Explicit behavior requested, but not a deterministic behavior
    # that this fixer knows how to implement safely.
    if any(signal in question_lower for signal in explicit_behavior_signals):
        return None

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    changed = False

    class ZeroDivisionFixer(ast.NodeTransformer):
        def visit_BinOp(self, node):
            nonlocal changed

            self.generic_visit(node)

            is_zero = (
                isinstance(node.right, ast.Constant)
                and node.right.value == 0
            )

            is_unsafe_operator = isinstance(
                node.op,
                (ast.Div, ast.FloorDiv, ast.Mod),
            )

            if is_zero and is_unsafe_operator:
                changed = True
                return node.left

            return node

    tree = ZeroDivisionFixer().visit(tree)
    ast.fix_missing_locations(tree)

    if not changed:
        return None

    try:
        return ast.unparse(tree)
    except Exception:
        return None


def validate_code_change(
    original_code: str,
    generated_code: str,
    validation_message: str,
) -> tuple[bool, str]:
    """
    Validate whether generated code fixes a known static problem
    without replacing the problematic operation with an unintended
    operation on the same expression.
    """

    if not original_code or not generated_code:
        return True, "Code change comparison not available."

    message_lower = validation_message.lower()

    # Handle division/modulo by zero detected by the static validator.
    if "division by zero" in message_lower:
        original_operations = extract_arithmetic_operations(original_code)
        generated_operations = extract_arithmetic_operations(generated_code)

        unsafe_original = [
            operation
            for operation in original_operations
            if operation.endswith(" / 0")
            or operation.endswith(" // 0")
            or operation.endswith(" % 0")
        ]

        unsafe_generated = [
            operation
            for operation in generated_operations
            if operation.endswith(" / 0")
            or operation.endswith(" // 0")
            or operation.endswith(" % 0")
        ]

        # The original unsafe operation is still present.
        if unsafe_generated:
            return (
                False,
                "The corrected code still contains the operation "
                "that caused the division-by-zero validation failure.",
            )

        # Examine the expression on the left side of the original
        # unsafe operation, for example:
        #
        #     result / 0
        #
        # left expression = result
        if unsafe_original:
            for operation in unsafe_original:
                parts = operation.rsplit(" / ", 1)

                if len(parts) != 2:
                    parts = operation.rsplit(" // ", 1)

                if len(parts) != 2:
                    parts = operation.rsplit(" % ", 1)

                if len(parts) == 2:
                    left_expression = parts[0].strip()

                    # If the generated code still performs division,
                    # floor division, or modulo using the same left
                    # expression, it may have changed the computation
                    # rather than fixing the original defect.
                    for generated_operation in generated_operations:
                        generated_parts = None

                        for operator in (" / ", " // ", " % "):
                            if operator in generated_operation:
                                generated_parts = generated_operation.rsplit(
                                    operator, 1
                                )
                                break

                        if not generated_parts or len(generated_parts) != 2:
                            continue

                        generated_left = generated_parts[0].strip()

                        if generated_left == left_expression:
                            return (
                                False,
                                "The corrected code changed the original "
                                "faulty arithmetic operation instead of "
                                "removing or safely fixing it.",
                            )

        # If the unsafe operation disappeared completely, this is a
        # potentially valid correction.
        return (
            True,
            "The problematic arithmetic operation was removed or "
            "safely changed.",
        )

    return True, "No specialized code-change comparison is required."


def validate_code_requirement(
    question: str,
    answer: str,
    task_type: str,
    artifact_type: str = "natural_language",
    language: str | None = None,
) -> tuple[bool, str]:
    """
    Check whether an engineering task received the expected artifact.
    """

    coding_tasks = {
        "code",
        "code_generation",
        "code_modification",
        "debugging",
        "testing",
        "refactoring",
        "sql_generation",
        "configuration_generation",
        "devops_task",
    }

    if task_type not in coding_tasks:
        return True, "No coding requirement."

    artifact = extract_artifact(
        answer,
        artifact_type,
        language,
    )

    if not artifact:
        return (
            False,
            f"The {task_type} request did not produce "
            f"identifiable {language or artifact_type} output.",
        )

    return True, "Required artifact was produced."


def is_code_task(task_type: str) -> bool:
    return task_type in {
        "code",
        "code_generation",
        "code_modification",
        "debugging",
        "testing",
        "refactoring",
        "sql_generation",
        "configuration_generation",
        "devops_task",
    }


def validate_yaml_syntax(yaml_text: str) -> tuple[bool, str]:
    """
    Validate YAML syntax without executing or applying the configuration.
    """
    try:
        import yaml

        yaml.safe_load(yaml_text)

        return True, "YAML syntax is valid."

    except Exception as exc:
        return False, f"YAML syntax error: {exc}"


def validate_json_syntax(json_text: str) -> tuple[bool, str]:
    """
    Validate JSON syntax.
    """
    import json

    try:
        json.loads(json_text)
        return True, "JSON syntax is valid."
    except json.JSONDecodeError as exc:
        return False, f"JSON syntax error: {exc}"


def validate_shell_syntax(shell_text: str) -> tuple[bool, str]:
    """
    Validate Bash syntax using bash -n without executing the script.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["bash", "-n"],
            input=shell_text,
            text=True,
            capture_output=True,
            timeout=5,
        )
    except Exception as exc:
        return False, f"Shell validation error: {exc}"

    if result.returncode == 0:
        return True, "Bash syntax is valid."

    error = result.stderr.strip() or "Unknown Bash syntax error."
    return False, f"Bash syntax error: {error}"


def validate_yaml_syntax(yaml_text: str) -> tuple[bool, str]:
    """
    Validate YAML syntax without executing or applying the configuration.
    """
    try:
        import yaml

        yaml.safe_load(yaml_text)

        return True, "YAML syntax is valid."

    except Exception as exc:
        return False, f"YAML syntax error: {exc}"


def validate_json_syntax(json_text: str) -> tuple[bool, str]:
    """
    Validate JSON syntax.
    """
    import json

    try:
        json.loads(json_text)
        return True, "JSON syntax is valid."
    except json.JSONDecodeError as exc:
        return False, f"JSON syntax error: {exc}"


def validate_shell_syntax(shell_text: str) -> tuple[bool, str]:
    """
    Validate Bash syntax using bash -n without executing the script.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["bash", "-n"],
            input=shell_text,
            text=True,
            capture_output=True,
            timeout=5,
        )
    except Exception as exc:
        return False, f"Shell validation error: {exc}"

    if result.returncode == 0:
        return True, "Bash syntax is valid."

    error = result.stderr.strip() or "Unknown Bash syntax error."
    return False, f"Bash syntax error: {error}"



def validate_python_requirements(
    question: str,
    code: str,
) -> tuple[bool, str]:
    """
    Validate basic Python requirements explicitly requested by the user.

    Currently validates:
    - requested function name
    - empty-list behavior returning 0
    """
    import re
    import ast

    question_lower = question.lower()

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"Python code could not be parsed: {exc}"

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    # ---------------------------------------------------------
    # 1. Requested function name
    # ---------------------------------------------------------
    name_match = re.search(
        r"\bfunction\s+(?:called\s+|named\s+)?([a-zA-Z_]\w*)",
        question,
        flags=re.IGNORECASE,
    )

    if name_match:
        requested_name = name_match.group(1)

        if not any(fn.name == requested_name for fn in functions):
            return (
                False,
                f"Requested function '{requested_name}' was not found.",
            )

    # ---------------------------------------------------------
    # 2. Empty-list behavior
    # ---------------------------------------------------------
    requires_empty_list_zero = (
        "empty list" in question_lower
        and (
            "return 0" in question_lower
            or "returns 0" in question_lower
        )
    )

    if requires_empty_list_zero:
        found_empty_list_guard = False

        for fn in functions:
            for node in ast.walk(fn):
                if not isinstance(node, ast.If):
                    continue

                test = node.test

                # Matches: if not lst:
                if isinstance(test, ast.UnaryOp) and isinstance(
                    test.op, ast.Not
                ):
                    if isinstance(test.operand, ast.Name):
                        for child in node.body:
                            if isinstance(child, ast.Return):
                                if (
                                    isinstance(child.value, ast.Constant)
                                    and child.value.value == 0
                                ):
                                    found_empty_list_guard = True

                # Matches: if len(lst) == 0:
                if isinstance(test, ast.Compare):
                    if (
                        len(test.ops) == 1
                        and isinstance(test.ops[0], ast.Eq)
                        and isinstance(test.left, ast.Call)
                        and isinstance(test.left.func, ast.Name)
                        and test.left.func.id == "len"
                        and len(test.left.args) == 1
                        and isinstance(test.left.args[0], ast.Name)
                        and len(test.comparators) == 1
                        and isinstance(
                            test.comparators[0],
                            ast.Constant,
                        )
                        and test.comparators[0].value == 0
                    ):
                        for child in node.body:
                            if isinstance(child, ast.Return):
                                if (
                                    isinstance(child.value, ast.Constant)
                                    and child.value.value == 0
                                ):
                                    found_empty_list_guard = True

        if not found_empty_list_guard:
            return (
                False,
                "The request requires returning 0 for an empty list, "
                "but no matching empty-list guard was found.",
            )

    return True, "Python requirements passed."


def validate_kubernetes_requirements(
    question: str,
    yaml_text: str,
) -> tuple[bool, str]:
    """
    Validate basic Kubernetes requirements explicitly requested
    by the user.

    Currently validates:
    - Deployment kind
    - requested replica count
    - presence of a container
    - requested Nginx application image
    """
    import re
    import yaml

    question_lower = question.lower()

    try:
        manifest = yaml.safe_load(yaml_text)
    except Exception as exc:
        return False, f"Kubernetes YAML could not be parsed: {exc}"

    if not isinstance(manifest, dict):
        return False, "Kubernetes manifest must be a YAML mapping."

    # ---------------------------------------------------------
    # 1. Kubernetes kind
    # ---------------------------------------------------------
    if "deployment" in question_lower:
        actual_kind = str(manifest.get("kind", "")).lower()

        if actual_kind != "deployment":
            return (
                False,
                f"Requested a Deployment, but manifest kind is "
                f"{manifest.get('kind')!r}.",
            )

    # ---------------------------------------------------------
    # 2. Replica count
    # ---------------------------------------------------------
    match = re.search(
        r"\b(\d+)\s+replicas?\b",
        question_lower,
    )

    if match:
        requested_replicas = int(match.group(1))
        actual_replicas = (
            manifest.get("spec", {}).get("replicas")
        )

        if actual_replicas != requested_replicas:
            return (
                False,
                f"Requested {requested_replicas} replicas, "
                f"but manifest specifies {actual_replicas!r}.",
            )

    # ---------------------------------------------------------
    # 3. Container presence
    # ---------------------------------------------------------
    containers = (
        manifest.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    )

    if not isinstance(containers, list) or not containers:
        return (
            False,
            "Kubernetes Deployment does not contain a container.",
        )

    # ---------------------------------------------------------
    # 4. Nginx image
    # ---------------------------------------------------------
    if "nginx" in question_lower:
        images = [
            str(container.get("image", "")).lower()
            for container in containers
            if isinstance(container, dict)
        ]

        if not any("nginx" in image for image in images):
            return (
                False,
                "Requested an Nginx application, but no "
                "container uses an Nginx image.",
            )

    return True, "Kubernetes requirements passed."


def validate_docker_compose_requirements(
    question: str,
    yaml_text: str,
) -> tuple[bool, str]:
    """
    Validate basic Docker Compose requirements explicitly requested
    by the user.

    Currently validates:
    - services section
    - application service presence
    - PostgreSQL service/image presence
    """
    import yaml

    question_lower = question.lower()

    try:
        compose = yaml.safe_load(yaml_text)
    except Exception as exc:
        return False, f"Docker Compose YAML could not be parsed: {exc}"

    if not isinstance(compose, dict):
        return False, "Docker Compose configuration must be a YAML mapping."

    services = compose.get("services")

    if not isinstance(services, dict) or not services:
        return False, "Docker Compose configuration has no services."

    # ---------------------------------------------------------
    # 1. PostgreSQL requirement
    # ---------------------------------------------------------
    if "postgres" in question_lower or "postgresql" in question_lower:
        postgres_services = []

        for name, service in services.items():
            if not isinstance(service, dict):
                continue

            image = str(service.get("image", "")).lower()

            if "postgres" in image or "postgresql" in image:
                postgres_services.append(name)

        if not postgres_services:
            return (
                False,
                "Requested PostgreSQL, but no service uses "
                "a PostgreSQL image.",
            )

    # ---------------------------------------------------------
    # 2. Application service
    # ---------------------------------------------------------
    if "application" in question_lower or "app" in question_lower:
        application_services = []

        for name, service in services.items():
            if not isinstance(service, dict):
                continue

            name_lower = str(name).lower()

            if (
                name_lower in {"app", "application", "python-app", "web"}
                or "build" in service
            ):
                application_services.append(name)

        if not application_services:
            return (
                False,
                "Requested an application service, but no "
                "application service was identified.",
            )

    return True, "Docker Compose requirements passed."


def validate_answer(
    question: str,
    answer: str,
    task_type: str,
    artifact_type: str = "natural_language",
    language: str | None = None,
) -> dict:
    """
    Route answer validation according to task and artifact type.
    """

    if not is_code_task(task_type):
        return {
            "valid": True,
            "validator": "none",
            "message": "No specialized validator required.",
        }

    # ---------------------------------------------------------
    # 1. Verify expected artifact exists
    # ---------------------------------------------------------

    requirement_valid, requirement_message = validate_code_requirement(
        question,
        answer,
        task_type,
        artifact_type,
        language,
    )

    if not requirement_valid:
        return {
            "valid": False,
            "validator": "artifact_requirement",
            "message": requirement_message,
        }

    # ---------------------------------------------------------
    # 2. Extract artifact
    # ---------------------------------------------------------

    artifact = extract_artifact(
        answer,
        artifact_type,
        language,
    )

    if not artifact:
        return {
            "valid": False,
            "validator": "artifact_extraction",
            "message": "Expected output artifact could not be extracted.",
        }

    # ---------------------------------------------------------
    # 3. Python
    # ---------------------------------------------------------

    if language == "python":
        code = extract_python_code(answer)

        if not code:
            return {
                "valid": False,
                "validator": "python_requirement",
                "message": "Expected Python code was not identified.",
            }

        valid, message = validate_python_syntax(code)

        if not valid:
            return {
                "valid": False,
                "validator": "python_syntax",
                "message": message,
            }

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(
                    node.op,
                    (ast.Div, ast.FloorDiv, ast.Mod),
                ):
                    if (
                        isinstance(node.right, ast.Constant)
                        and node.right.value == 0
                    ):
                        return {
                            "valid": False,
                            "validator": "python_static",
                            "message": "Possible division by zero detected.",
                        }

        except SyntaxError as exc:
            return {
                "valid": False,
                "validator": "python_syntax",
                "message": f"Python syntax error: {exc}",
            }

        # -----------------------------------------------------
        # Python requirement validation
        # -----------------------------------------------------
        requirements_valid, requirements_message = (
            validate_python_requirements(question, code)
        )

        if not requirements_valid:
            return {
                "valid": False,
                "validator": "python_requirement",
                "message": requirements_message,
            }

        return {
            "valid": True,
            "validator": "python_requirement",
            "message": requirements_message,
        }

    # ---------------------------------------------------------
    # 4. SQL
    # ---------------------------------------------------------

    if language == "sql":
        # SQL is intentionally not executed against a database.
        # We perform conservative structural checks here.
        sql = artifact.strip()

        if not sql:
            return {
                "valid": False,
                "validator": "sql_basic",
                "message": "SQL output is empty.",
            }

        sql_lower = sql.lower().strip()

        sql_keywords = (
            "select",
            "insert",
            "update",
            "delete",
            "with",
            "create",
            "alter",
            "drop",
        )

        if not sql_lower.startswith(sql_keywords):
            return {
                "valid": False,
                "validator": "sql_basic",
                "message": "SQL output does not begin with a recognized SQL statement.",
            }

        return {
            "valid": True,
            "validator": "sql_basic",
            "message": "Basic SQL structure passed.",
        }

    # ---------------------------------------------------------
    # 5. YAML
    # ---------------------------------------------------------

    if language == "yaml":
        valid, message = validate_yaml_syntax(artifact)

        if not valid:
            return {
                "valid": False,
                "validator": "yaml_syntax",
                "message": message,
            }

        # Kubernetes gets an additional requirement-level check.
        if artifact_type == "kubernetes_manifest":
            requirements_valid, requirements_message = (
                validate_kubernetes_requirements(question, artifact)
            )

            if not requirements_valid:
                return {
                    "valid": False,
                    "validator": "kubernetes_requirement",
                    "message": requirements_message,
                }

            return {
                "valid": True,
                "validator": "kubernetes_requirement",
                "message": requirements_message,
            }

        # Docker Compose gets an additional requirement-level check.
        if artifact_type == "docker_compose":
            requirements_valid, requirements_message = (
                validate_docker_compose_requirements(question, artifact)
            )

            if not requirements_valid:
                return {
                    "valid": False,
                    "validator": "docker_compose_requirement",
                    "message": requirements_message,
                }

            return {
                "valid": True,
                "validator": "docker_compose_requirement",
                "message": requirements_message,
            }

        return {
            "valid": True,
            "validator": "yaml_syntax",
            "message": message,
        }

    # ---------------------------------------------------------
    # 6. Bash
    # ---------------------------------------------------------

    if language == "bash":
        valid, message = validate_shell_syntax(artifact)

        if not valid:
            return {
                "valid": False,
                "validator": "shell_syntax",
                "message": message,
            }

        return {
            "valid": True,
            "validator": "shell_syntax",
            "message": message,
        }

    # ---------------------------------------------------------
    # 7. JSON
    # ---------------------------------------------------------

    if language == "json":
        valid, message = validate_json_syntax(artifact)

        if not valid:
            return {
                "valid": False,
                "validator": "json_syntax",
                "message": message,
            }

        return {
            "valid": True,
            "validator": "json_syntax",
            "message": message,
        }

    # ---------------------------------------------------------
    # 8. Unknown artifact
    # ---------------------------------------------------------

    return {
        "valid": True,
        "validator": "artifact_basic",
        "message": (
            f"Artifact '{artifact_type}' with language "
            f"'{language}' was produced."
        ),
    }

