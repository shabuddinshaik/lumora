#!/usr/bin/env python3

import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
MAX_LOG_CHARS = 12000
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")

LEGACY_TARGETS = {
    "healthy": "lumora-test-healthy",
    "failing": "lumora-test-failing",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def run_docker(args, timeout=15):
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    ).stdout


def write_json_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".snapshot-",
        suffix=".tmp",
        delete=False,
    ) as temp:
        json.dump(data, temp, indent=2)
        temp.write("\n")
        temp_path = Path(temp.name)

    # Keep snapshots readable by the diagnostics collector.
    # The evidence directory's setgid bit supplies its group.
    temp_path.chmod(0o640)
    temp_path.replace(path)


def safe_docker_call(args, timeout=15):
    try:
        return run_docker(args, timeout=timeout), None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        message = getattr(exc, "stderr", None) or str(exc)
        return None, message[-1000:]


def collect_metrics(container_id, running):
    if not running:
        return {
            "available": False,
            "collected_at": now(),
            "reason": "Container is stopped; live resource metrics are unavailable.",
        }

    output, error = safe_docker_call([
        "stats", "--no-stream", "--format", "{{json .}}", container_id
    ])

    if error or not output:
        return {
            "available": False,
            "collected_at": now(),
            "reason": "Docker resource metrics could not be collected.",
        }

    try:
        stats = json.loads(output.strip())
    except json.JSONDecodeError:
        return {
            "available": False,
            "collected_at": now(),
            "reason": "Docker returned invalid resource metrics.",
        }

    memory_usage = stats.get("MemUsage", "")
    memory_used, memory_limit = (
        memory_usage.split(" / ", 1)
        if " / " in memory_usage
        else (None, None)
    )

    return {
        "available": True,
        "collected_at": now(),
        "cpu_percent": stats.get("CPUPerc"),
        "memory_usage": memory_usage or None,
        "memory_used": memory_used,
        "memory_limit": memory_limit,
        "memory_percent": stats.get("MemPerc"),
        "network_io": stats.get("NetIO"),
        "block_io": stats.get("BlockIO"),
        "pids": stats.get("PIDs"),
    }


def collect_container(container_id):
    if not CONTAINER_ID_RE.fullmatch(container_id):
        raise ValueError("Invalid Docker container ID")

    raw, error = safe_docker_call(["inspect", container_id])
    if error or not raw:
        return None

    try:
        inspection = json.loads(raw)[0]
    except (json.JSONDecodeError, IndexError, TypeError):
        return None

    state = inspection.get("State") or {}
    config = inspection.get("Config") or {}
    running = state.get("Running") is True
    status = state.get("Status", "unknown")

    logs, log_error = safe_docker_call([
        "logs", "--tail", "50", container_id
    ])
    if logs is None:
        logs = f"Unable to retrieve logs: {(log_error or 'unknown error')}"
    logs = logs[-MAX_LOG_CHARS:]

    labels = config.get("Labels") or {}
    health = (state.get("Health") or {}).get("Status")

    evidence = {
        "id": container_id,
        "short_id": container_id[:12],
        "container": inspection.get("Name", "").lstrip("/"),
        "image": config.get("Image"),
        "created": inspection.get("Created"),
        "started_at": state.get("StartedAt"),
        "finished_at": state.get("FinishedAt"),
        "status": status,
        "running": running,
        "health": health,
        "exit_code": state.get("ExitCode"),
        "restart_count": inspection.get("RestartCount", 0),
        "labels": labels,
        "metrics": collect_metrics(container_id, running),
        "logs": logs,
        "logs_available": log_error is None,
        "collected_at": now(),
        "evidence_source": "Read-only Docker inspect, logs, and stats",
    }

    write_json_atomic(EVIDENCE_DIR / f"container-{container_id}.json", evidence)
    return evidence


def main():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    ids_output = run_docker(["ps", "-aq", "--no-trunc"], timeout=30)
    container_ids = sorted({
        item.strip()
        for item in ids_output.splitlines()
        if CONTAINER_ID_RE.fullmatch(item.strip())
    })

    containers = []
    failures = []

    for container_id in container_ids:
        try:
            evidence = collect_container(container_id)
            if evidence is not None:
                containers.append({
                    key: evidence.get(key)
                    for key in (
                        "id", "short_id", "container", "image", "created",
                        "started_at", "finished_at", "status", "running",
                        "health", "exit_code", "restart_count",
                        "collected_at",
                    )
                })
            else:
                failures.append({"id": container_id, "reason": "Inspect unavailable"})
        except Exception as exc:
            failures.append({
                "id": container_id,
                "reason": str(exc)[:500],
            })

    inventory = {
        "collected_at": now(),
        "total_discovered": len(container_ids),
        "total_collected": len(containers),
        "total_failed": len(failures),
        "containers": containers,
        "collection_errors": failures,
    }
    write_json_atomic(EVIDENCE_DIR / "inventory.json", inventory)

    # Preserve the legacy snapshots and endpoint behavior.
    for target, name in LEGACY_TARGETS.items():
        matches = [c for c in containers if c["container"] == name]
        if not matches:
            print(f"Legacy target {target}: container not found")
            continue

        path = EVIDENCE_DIR / f"container-{matches[0]['id']}.json"
        try:
            evidence = json.loads(path.read_text(encoding="utf-8"))
            evidence["target"] = target
            write_json_atomic(EVIDENCE_DIR / f"{target}.json", evidence)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Legacy target {target}: snapshot update failed: {exc}")

    print(
        f"Inventory collected: discovered={len(container_ids)}, "
        f"collected={len(containers)}, failed={len(failures)}"
    )


if __name__ == "__main__":
    main()
