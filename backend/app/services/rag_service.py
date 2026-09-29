from sqlalchemy.orm import Session

from app.agents.retrieval_agent import retrieve_with_agent
from app.agents.task_analyzer import analyze_task
from app.agents.answer_validator import (
    validate_answer,
    extract_python_code,
    validate_code_change,
    deterministic_code_fix,
)
from app.models.evaluation import EvaluationRun
from app.services.context_formatter import format_context
from app.services.llm_service import generate_answer, refine_answer
from app.services.prompt_builder import build_answer_prompt
from app.services.timing import elapsed, now


def generate_rag_answer(
    db: Session,
    question: str,
    top_k: int = 5,
    document_id: int | None = None,
    task_type: str = "auto",
) -> dict:
    total_start = now()

    # ---------------------------------------------------------
    # 1. Understand the task
    # ---------------------------------------------------------
    task_analysis = analyze_task(question)

    print(
        "[Task Decision] "
        f"type={task_analysis.task_type} "
        f"complexity={task_analysis.complexity} "
        f"requires_retrieval={task_analysis.requires_retrieval}"
    )

    # ---------------------------------------------------------
    # 2. Direct LLM path
    # ---------------------------------------------------------
    if not task_analysis.requires_retrieval:
        retrieval_latency = 0.0

        generation_start = now()

        prompt = build_answer_prompt(
            question,
            "",
            use_context=False,
        )

        generation_result = generate_answer(prompt)

        answer = generation_result["response"]

        print("[Generated Answer]")
        print(answer)
        prompt_tokens = generation_result["prompt_tokens"]
        completion_tokens = generation_result["completion_tokens"]
        total_tokens = generation_result["total_tokens"]

        validation_result = validate_answer(
            question,
            answer,
            task_analysis.task_type,
            task_analysis.artifact_type,
            task_analysis.language,
        )

        print(
            "[Answer Validation] "
            f"valid={validation_result['valid']} "
            f"validator={validation_result['validator']} "
            f"message={validation_result['message']}"
        )

        # -----------------------------------------------------
        # One controlled correction/refinement attempt
        # -----------------------------------------------------
        if not validation_result["valid"]:
            print("[Answer Correction] First answer failed validation.")

            original_answer = answer
            original_validation_message = validation_result["message"]

            # First try a deterministic correction for known static errors.
            deterministic_fix_applied = False

            if (
                task_analysis.language == "python"
                and task_analysis.task_type in {
                    "code",
                    "code_generation",
                    "code_modification",
                    "debugging",
                    "testing",
                    "refactoring",
                }
            ):
                original_code = extract_python_code(answer)

                if original_code:
                    fixed_code = deterministic_code_fix(
                        code=original_code,
                        validation_message=original_validation_message,
                        question=question,
                    )

                    if fixed_code:
                        print("[Deterministic Fix] Candidate correction generated.")

                        deterministic_validation = validate_answer(
                            question,
                            fixed_code,
                            task_analysis.task_type,
                            task_analysis.artifact_type,
                            task_analysis.language,
                        )

                        print(
                            "[Deterministic Fix Validation] "
                            f"valid={deterministic_validation['valid']} "
                            f"validator={deterministic_validation['validator']} "
                            f"message={deterministic_validation['message']}"
                        )

                        if deterministic_validation["valid"]:
                            answer = fixed_code
                            validation_result = deterministic_validation
                            deterministic_fix_applied = True

                            print(
                                "[Deterministic Fix] "
                                "Accepted validated correction."
                            )

            # If deterministic correction was not sufficient,
            # fall back to the existing LLM refinement.
            if not deterministic_fix_applied:
                print("[Answer Refinement] Starting LLM correction.")

                refinement_result = refine_answer(
                    question=question,
                    previous_answer=answer,
                    validation_message=original_validation_message,
                    task_type=task_analysis.task_type,
                )

                answer = refinement_result["response"]

                prompt_tokens += refinement_result["prompt_tokens"]
                completion_tokens += refinement_result["completion_tokens"]
                total_tokens += refinement_result["total_tokens"]

                validation_result = validate_answer(
                    question,
                    answer,
                    task_analysis.task_type,
                    task_analysis.artifact_type,
                    task_analysis.language,
                )

                print(
                    "[Answer Validation Retry] "
                    f"valid={validation_result['valid']} "
                    f"validator={validation_result['validator']} "
                    f"message={validation_result['message']}"
                )

                # Additional semantic-preservation check for code corrections.
                if (
                    validation_result["valid"]
                    and task_analysis.language == "python"
                    and task_analysis.task_type in {
                        "code",
                        "code_generation",
                        "code_modification",
                        "debugging",
                        "testing",
                        "refactoring",
                    }
                ):
                    original_code = extract_python_code(original_answer)
                    refined_code = extract_python_code(answer)

                    if original_code and refined_code:
                        change_validation = validate_code_change(
                            original_code=original_code,
                            generated_code=refined_code,
                            validation_message=original_validation_message,
                        )

                        print(
                            "[Code Change Validation] "
                            f"valid={change_validation[0]} "
                            f"message={change_validation[1]}"
                        )

                        if not change_validation[0]:
                            validation_result = {
                                "valid": False,
                                "validator": "code_change",
                                "message": change_validation[1],
                            }

            if not validation_result["valid"]:
                answer = (
                    "I could not produce a validated answer for this request. "
                    f"The generated response failed validation: "
                    f"{validation_result['message']}"
                )

        generation_latency = elapsed(generation_start)
        total_latency = elapsed(total_start)

        evaluation = EvaluationRun(
            question=question,
            system_type="agentic_rag",
            selected_strategy="none",
            final_strategy="none",
            fallback_count=0,
            total_retrieved_count=0,
            final_retrieved_count=0,
            selected_context_count=0,
            evidence_sufficient=True,
            retrieval_latency_seconds=0.0,
            generation_latency_seconds=round(generation_latency, 4),
            total_latency_seconds=round(total_latency, 4),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        db.add(evaluation)
        db.commit()

        return {
            "question": question,
            "answer": answer,
            "selected_strategy": "none",
            "final_strategy": "none",
            "context_sufficient": True,
            "attempts": [],
            "sources": [],
            "fallback_count": 0,
            "selected_context_count": 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency": {
                "retrieval_seconds": 0.0,
                "generation_seconds": round(generation_latency, 4),
                "total_seconds": round(total_latency, 4),
            },
        }

    # ---------------------------------------------------------
    # 3. Retrieval path
    # ---------------------------------------------------------
    retrieval_start = now()

    retrieval = retrieve_with_agent(
        db,
        question,
        top_k=top_k,
        document_id=document_id,
        task_type=task_type,
    )

    retrieval_latency = elapsed(retrieval_start)

    context = format_context(retrieval["results"])

    # ---------------------------------------------------------
    # 4. Generate answer from retrieved context
    # ---------------------------------------------------------
    generation_start = now()

    if not retrieval["context_sufficient"]:
        answer = (
            "The available learning materials do not contain enough "
            "information to answer this question."
        )

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

    else:
        prompt = build_answer_prompt(
            question,
            context,
        )

        generation_result = generate_answer(prompt)

        answer = generation_result["response"]
        prompt_tokens = generation_result["prompt_tokens"]
        completion_tokens = generation_result["completion_tokens"]
        total_tokens = generation_result["total_tokens"]

    generation_latency = elapsed(generation_start)
    total_latency = elapsed(total_start)

    # ---------------------------------------------------------
    # 5. Sources
    # ---------------------------------------------------------
    sources = [
        {
            "document_id": result["chunk"].document_id,
            "chunk_id": result["chunk"].id,
            "score": result["score"],
            "retrieval_method": result["retrieval_method"],
        }
        for result in retrieval["results"]
    ]

    attempts = retrieval["attempts"]

    fallback_count = max(len(attempts) - 1, 0)

    total_retrieved_count = sum(
        attempt.get("result_count", 0)
        for attempt in attempts
    )

    final_retrieved_count = 0

    if retrieval["final_strategy"] is not None:
        final_attempt = next(
            (
                attempt
                for attempt in reversed(attempts)
                if attempt["strategy"] == retrieval["final_strategy"]
            ),
            None,
        )

        if final_attempt is not None:
            final_retrieved_count = final_attempt.get(
                "result_count",
                0,
            )

    selected_context_count = len(retrieval["results"])

    # ---------------------------------------------------------
    # 6. Save evaluation
    # ---------------------------------------------------------
    evaluation = EvaluationRun(
        question=question,
        system_type="agentic_rag",
        selected_strategy=retrieval["selected_strategy"],
        final_strategy=retrieval["final_strategy"],
        fallback_count=fallback_count,
        total_retrieved_count=total_retrieved_count,
        final_retrieved_count=final_retrieved_count,
        selected_context_count=selected_context_count,
        evidence_sufficient=retrieval["context_sufficient"],
        retrieval_latency_seconds=round(retrieval_latency, 4),
        generation_latency_seconds=round(generation_latency, 4),
        total_latency_seconds=round(total_latency, 4),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    db.add(evaluation)
    db.commit()

    # ---------------------------------------------------------
    # 7. Return API response
    # ---------------------------------------------------------
    return {
        "question": question,
        "answer": answer,
        "selected_strategy": retrieval["selected_strategy"],
        "final_strategy": retrieval["final_strategy"],
        "context_sufficient": retrieval["context_sufficient"],
        "attempts": retrieval["attempts"],
        "sources": sources,
        "fallback_count": fallback_count,
        "selected_context_count": selected_context_count,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency": {
            "retrieval_seconds": round(retrieval_latency, 4),
            "generation_seconds": round(generation_latency, 4),
            "total_seconds": round(total_latency, 4),
        },
    }
