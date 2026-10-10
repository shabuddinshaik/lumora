import os
import re

import requests
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(
    prefix="/api/v1/devops",
    tags=["devops-diagnostics"],
)

COLLECTOR_URL = os.getenv(
    "LUMORA_DIAGNOSTICS_URL",
    "http://lumora-diagnostics:8081",
).rstrip("/")

ALLOWED_TARGETS = {"healthy", "failing"}
REQUEST_TIMEOUT = 5


def fetch_evidence(target: str) -> dict:
    try:
        response = requests.get(
            f"{COLLECTOR_URL}/containers/{target}/diagnostics",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve diagnostic evidence",
        )


def analyze_evidence(evidence: dict) -> dict:
    status = evidence.get("status")
    exit_code = evidence.get("exit_code")
    logs = evidence.get("logs") or ""

    observations = []
    recommendations = []
    confidence = "low"

    if status == "running":
        observations.append("The container is currently reported as running.")

    elif status == "exited":
        observations.append("The container is reported as exited.")

    else:
        observations.append(
            "The container state is missing or not recognized."
        )

    if exit_code not in (None, 0):
        observations.append(f"The recorded exit code is {exit_code}.")

    if "ERROR: simulated database connection failure" in logs:
        observations.append(
            "Logs contain the known simulated database connection failure."
        )
        recommendations.append(
            "Inspect the application startup path and database connection "
            "handling in the test workload."
        )
        diagnosis = (
            "The test container exited with code 1 after logging the "
            "simulated database connection failure. This confirms the "
            "observed failure sequence, but does not establish a real "
            "database outage."
        )
        confidence = "high"

    elif status == "running" and "APP_STATUS=healthy" in logs:
        observations.append(
            "Logs contain the expected APP_STATUS=healthy marker."
        )
        diagnosis = (
            "The container is running and emits the expected healthy marker. "
            "This does not independently verify application or dependency "
            "health."
        )
        recommendations.append(
            "For stronger health assurance, add a real application health "
            "check and verify its dependencies."
        )
        confidence = "high"

    else:
        diagnosis = (
            "The available evidence is insufficient to determine the "
            "underlying cause."
        )
        recommendations.append(
            "Collect fresh logs and container state, then inspect the "
            "application-specific health signals."
        )

    return {
        "diagnosis": diagnosis,
        "observations": observations,
        "recommendations": recommendations,
        "confidence": confidence,
        "limitations": [
            "This diagnosis uses deterministic rules, not an LLM.",
            "Evidence comes from the latest saved snapshot, not a live query.",
            "Confidence describes the match to known test evidence, not "
            "general production diagnostic accuracy.",
        ],
    }


@router.get("/diagnose")
def diagnose(
    target: str = Query(..., description="Approved target: healthy or failing"),
):
    if target not in ALLOWED_TARGETS:
        raise HTTPException(
            status_code=404,
            detail="Target is not allowlisted",
        )

    evidence = fetch_evidence(target)

    return {
        "target": target,
        "container": evidence.get("container"),
        "collected_at": evidence.get("collected_at"),
        "evidence": {
            "status": evidence.get("status"),
            "running": evidence.get("running"),
            "exit_code": evidence.get("exit_code"),
            "restart_count": evidence.get("restart_count"),
            "metrics": evidence.get("metrics"),
            "logs": evidence.get("logs"),
        },
        "analysis": analyze_evidence(evidence),
    }


# Dynamic container inventory endpoints.
# These proxy saved evidence from the read-only diagnostics collector.
CONTAINER_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def fetch_collector_json(path: str) -> dict:
    try:
        response = requests.get(
            f"{COLLECTOR_URL}{path}",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve container inventory from diagnostics collector",
        )
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Diagnostics collector returned invalid JSON",
        )


@router.get("/containers")
def list_containers():
    """Return the latest saved inventory of discovered Docker containers."""
    return fetch_collector_json("/inventory")


@router.get("/containers/{container_id}")
def get_container(container_id: str):
    """Return evidence for a container present in the latest inventory."""
    if not CONTAINER_ID_PATTERN.fullmatch(container_id):
        raise HTTPException(status_code=400, detail="Invalid container ID")

    return fetch_collector_json(f"/inventory/{container_id}")


# Generalized, deterministic assessment for any discovered container.
# This uses saved collector evidence only and does not take operational action.
def assess_container_evidence(evidence: dict) -> dict:
    status = evidence.get("status")
    exit_code = evidence.get("exit_code")
    restart_count = evidence.get("restart_count")
    health = evidence.get("health")
    metrics = evidence.get("metrics") or {}
    logs = evidence.get("logs") or ""

    observations = []
    recommendations = []
    findings = []
    severity = "info"
    confidence = "low"

    if status == "exited":
        observations.append("The container was exited when evidence was collected.")
        if exit_code not in (None, 0):
            severity = "high"
            findings.append("non_zero_exit")
            observations.append(f"The recorded exit code is {exit_code}.")
            recommendations.append(
                "Read the collected logs and verify the container's startup "
                "command and exit conditions."
            )
            if "ERROR: simulated database connection failure" in logs:
                findings.append("known_simulated_database_failure")
                observations.append(
                    "The logs match the known simulated database failure test; "
                    "this is not evidence of a real database outage."
                )
                confidence = "high"
            else:
                confidence = "medium"
        elif exit_code == 0:
            findings.append("exited_successfully")
            observations.append(
                "The container exited with code 0; this may be expected for "
                "a one-shot workload."
            )
            recommendations.append(
                "Verify whether this container is intended to run continuously "
                "or complete and exit."
            )
        else:
            severity = "medium"
            findings.append("exited_without_exit_code")
            recommendations.append(
                "Inspect the saved lifecycle details and collect a fresh snapshot."
            )

    elif status == "running":
        observations.append("The container was running when evidence was collected.")
        if exit_code not in (None, 0):
            observations.append(
                f"The saved evidence also contains exit code {exit_code}; "
                "confirm which lifecycle event it describes."
            )
            findings.append("exit_code_needs_context")
        if health in ("unhealthy", "starting"):
            severity = "high" if health == "unhealthy" else "medium"
            findings.append(f"health_{health}")
            observations.append(f"Docker reported health status: {health}.")
            recommendations.append(
                "Inspect the configured health check and its recorded failures."
            )
        elif health == "healthy":
            observations.append("Docker reported the configured health check as healthy.")
        elif health in (None, "", "not configured"):
            observations.append("No configured Docker health-check result is available.")

    else:
        severity = "medium"
        findings.append("unknown_status")
        observations.append("The saved container status is missing or unrecognized.")
        recommendations.append(
            "Verify the container's current state with a fresh read-only snapshot."
        )

    if isinstance(restart_count, int) and restart_count > 0:
        severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3}
        severity = max(
            severity,
            "medium" if restart_count >= 3 else "low",
            key=lambda item: severity_order[item],
        )
        findings.append("restarts_observed")
        observations.append(f"The saved restart count is {restart_count}.")
        recommendations.append(
            "Review the previous logs and lifecycle timestamps to determine "
            "whether restarts are recurring."
        )

    memory_percent = metrics.get("memory_percent")
    if isinstance(memory_percent, (int, float)):
        if memory_percent >= 90:
            severity = "high"
            findings.append("high_memory_usage")
            observations.append(
                f"Memory usage was {memory_percent:.1f}% of the reported limit."
            )
            recommendations.append(
                "Verify the memory limit, workload demand, and trend across "
                "multiple snapshots before changing resource settings."
            )
        elif memory_percent >= 80:
            severity = max(
                severity, "medium",
                key={"info": 0, "low": 1, "medium": 2, "high": 3}.get,
            )
            findings.append("elevated_memory_usage")
            observations.append(
                f"Memory usage was {memory_percent:.1f}% of the reported limit."
            )
            recommendations.append(
                "Compare memory usage across snapshots and check for sustained growth."
            )

    if isinstance(logs, str) and logs.strip():
        observations.append("Collected container logs are available for review.")
        if "ERROR: simulated database connection failure" in logs:
            findings.append("known_simulated_database_failure")
            observations.append(
                "Logs contain the known simulated database connection failure; "
                "this does not prove a real database outage."
            )
            recommendations.append(
                "Check the workload's configured database endpoint and startup handling."
            )

    # Application-level signals from saved logs.
    # These are supporting indicators, not independent health checks.
    if isinstance(logs, str) and logs.strip():
        log_lines = [line.strip() for line in logs.splitlines() if line.strip()]
        healthy_marker_count = sum(
            "APP_STATUS=healthy" in line for line in log_lines
        )

        if status == "running" and healthy_marker_count:
            findings.append("application_healthy_log_signal")
            observations.append(
                f"Saved logs contain APP_STATUS=healthy "
                f"({healthy_marker_count} matching line(s)); this is a "
                "positive application log signal, not independent proof of health."
            )
            recommendations.append(
                "Confirm the application health signal against an application "
                "health endpoint or a configured Docker health check."
            )

        error_markers = (
            "ERROR",
            "CRITICAL",
            "FATAL",
            "Traceback (most recent call last)",
        )
        matching_error_lines = [
            line for line in log_lines
            if any(marker.lower() in line.lower() for marker in error_markers)
            and "ERROR: simulated database connection failure" not in line
        ]

        if matching_error_lines:
            findings.append("application_error_log_signal")
            observations.append(
                f"Saved logs contain {len(matching_error_lines)} line(s) "
                "matching common error markers; review the surrounding log context."
            )
            recommendations.append(
                "Inspect the matching error lines and nearby timestamps before "
                "concluding that the application has failed."
            )

    if not recommendations:
        recommendations.append(
            "Review the saved logs and application-specific health signals; "
            "running status alone does not prove application health."
        )

    return {
        "assessment_type": "deterministic_evidence_rules",
        "severity": severity,
        "findings": list(dict.fromkeys(findings)),
        "diagnosis": (
            "Potential operational issue indicated by saved evidence."
            if severity in ("medium", "high")
            else "No decisive failure was established by the available evidence."
        ),
        "observations": observations,
        "recommendations": list(dict.fromkeys(recommendations)),
        "confidence": confidence,
        "evidence_collected_at": evidence.get("collected_at"),
        "limitations": [
            "Assessment uses the latest saved snapshot, not live measurements.",
            "Rules identify evidence patterns and do not prove root cause.",
            "Resource thresholds are heuristic and should be interpreted in context.",
            "No container, service, or infrastructure changes are performed.",
        ],
    }


@router.get("/containers/{container_id}/assessment")
def assess_container(container_id: str):
    """Assess saved evidence for any container in the latest inventory."""
    if not CONTAINER_ID_PATTERN.fullmatch(container_id):
        raise HTTPException(status_code=400, detail="Invalid container ID")

    evidence = fetch_collector_json(f"/inventory/{container_id}")
    assessment = assess_container_evidence(evidence)

    return {
        "container": evidence.get("container"),
        "container_id": container_id,
        "status": evidence.get("status"),
        "exit_code": evidence.get("exit_code"),
        "restart_count": evidence.get("restart_count"),
        "health": evidence.get("health"),
        "metrics": evidence.get("metrics") or {},
        "assessment": assessment,
    }


@router.get("/host-assessment")
def assess_host_ssh():
    """Assess sanitized, saved host SSH and kernel evidence."""
    evidence = fetch_collector_json("/host/ssh")

    ssh = evidence.get("ssh") or {}
    kernel = evidence.get("kernel") or {}

    def count(section, name):
        value = section.get(name) or {}
        result = value.get("count", 0)
        return result if isinstance(result, int) and result >= 0 else 0

    auth_success = count(ssh, "authentication_success")
    auth_failure = count(ssh, "authentication_failure")
    preauth_disconnect = count(ssh, "preauth_disconnect")
    established_disconnect = count(ssh, "established_disconnect")
    resource_pressure = count(kernel, "resource_pressure")
    io_network = count(kernel, "io_network_or_panic")

    findings = []
    observations = []
    recommendations = []
    severity = "info"
    confidence = "low"

    if auth_failure:
        findings.append("ssh_authentication_failures")
        observations.append(
            f"{auth_failure} SSH authentication failure event(s) were recorded "
            f"within the last {evidence.get('window_minutes', 30)} minutes."
        )
        recommendations.append(
            "Review SSH authentication policy, restrict SSH access to trusted "
            "sources where practical, and use key-based authentication."
        )
        if auth_failure >= 100:
            severity = "medium"
            observations.append(
                "The authentication-failure count is elevated; automated "
                "scanning is a possible explanation, not a confirmed attribution."
            )
        else:
            severity = "low"

    if preauth_disconnect:
        findings.append("unauthenticated_connections_ended")
        observations.append(
            f"{preauth_disconnect} unauthenticated connection-ending event(s) "
            "were recorded. These are kept separate from established-session events."
        )

    if auth_success:
        observations.append(
            f"{auth_success} SSH authentication success event(s) were recorded; "
            "the events are not attributed to a particular person or session."
        )

    if established_disconnect:
        findings.append("ssh_session_disconnect_events")
        observations.append(
            f"{established_disconnect} established-connection disconnect event(s) "
            "matched the collector's rules. They may include sessions other "
            "than the user's affected terminal."
        )
        recommendations.append(
            "Compare disconnect timestamps with the affected SSH client's "
            "local logs and reconnect time before attributing the cause."
        )
        if severity == "info":
            severity = "low"

    if resource_pressure:
        findings.append("kernel_resource_pressure_events")
        observations.append(
            f"{resource_pressure} kernel resource-pressure event(s) matched "
            "the collector's rules."
        )
        recommendations.append(
            "Inspect the corresponding system journal timestamps and resource "
            "usage before attributing a disconnect to memory pressure."
        )
        severity = "high"

    if io_network:
        findings.append("kernel_io_network_or_panic_events")
        observations.append(
            f"{io_network} kernel I/O, network, or panic event(s) matched "
            "the collector's rules."
        )
        recommendations.append(
            "Inspect the matching system journal entries and VM/network "
            "monitoring for the same time window."
        )
        severity = "high"

    if not observations:
        observations.append(
            "No matching SSH or kernel events were found in the saved evidence."
        )
        recommendations.append(
            "If the disconnect recurs, record its exact time and compare it "
            "with a fresh host snapshot and the SSH client's error message."
        )

    if established_disconnect and not resource_pressure and not io_network:
        diagnosis = (
            "SSH disconnect events were observed, but the available evidence "
            "does not establish why the terminal disconnected."
        )
    elif auth_failure and not established_disconnect:
        diagnosis = (
            "SSH authentication failures were observed, but these do not "
            "explain an established terminal session disconnecting."
        )
    elif resource_pressure or io_network:
        diagnosis = (
            "Kernel warning events were observed in the collection window. "
            "Their timing and relationship to the SSH issue require verification."
        )
    else:
        diagnosis = (
            "The available host evidence does not establish the cause of "
            "the reported SSH terminal disconnect."
        )

    return {
        "assessment_type": "deterministic_host_evidence_rules",
        "severity": severity,
        "diagnosis": diagnosis,
        "findings": list(dict.fromkeys(findings)),
        "observations": observations,
        "evidence": {
            "window_minutes": evidence.get("window_minutes"),
            "collected_at": evidence.get("collected_at"),
            "ssh": {
                "authentication_success": auth_success,
                "authentication_failure": auth_failure,
                "preauth_disconnect": preauth_disconnect,
                "established_disconnect": established_disconnect,
            },
            "kernel": {
                "resource_pressure": resource_pressure,
                "io_network_or_panic": io_network,
            },
            "uptime_summary": evidence.get("uptime_summary"),
            "memory_summary": evidence.get("memory_summary"),
            "root_disk_summary": evidence.get("root_disk_summary"),
        },
        "recommendations": list(dict.fromkeys(recommendations)),
        "confidence": confidence,
        "limitations": evidence.get("limitations", []) + [
            "Severity describes observed evidence patterns, not confirmed root cause.",
            "SSH events are not correlated to a specific client session.",
            "This endpoint reads saved evidence and does not change host configuration.",
        ],
    }


@router.get("/correlate")
def correlate_container_evidence():
    """Correlate saved container evidence without changing infrastructure."""
    from collections import defaultdict
    from datetime import datetime, timezone

    inventory = fetch_collector_json("/inventory")
    containers = inventory.get("containers", [])

    if not isinstance(containers, list):
        raise HTTPException(
            status_code=502,
            detail="Diagnostics collector returned an invalid inventory structure",
        )

    results = []
    projects = defaultdict(list)
    severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3}

    def parse_time(value):
        if not isinstance(value, str) or not value:
            return None
        if value.startswith("0001-01-01"):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    for item in containers:
        container_id = item.get("id")
        if not isinstance(container_id, str) or not CONTAINER_ID_PATTERN.fullmatch(container_id):
            continue

        evidence = fetch_collector_json(f"/inventory/{container_id}")
        labels = evidence.get("labels") or {}
        if not isinstance(labels, dict):
            labels = {}

        project = labels.get("com.docker.compose.project")
        service = labels.get("com.docker.compose.service")
        status = evidence.get("status", item.get("status"))
        health = evidence.get("health", item.get("health"))
        exit_code = evidence.get("exit_code", item.get("exit_code"))
        restart_count = evidence.get("restart_count", item.get("restart_count", 0))
        severity = "info"
        signals = []

        if status == "exited" and isinstance(exit_code, int) and exit_code != 0:
            severity = "high"
            signals.append({
                "type": "non_zero_exit",
                "evidence": f"Container exited with code {exit_code}.",
            })
        elif health == "unhealthy":
            severity = "high"
            signals.append({
                "type": "unhealthy",
                "evidence": "Docker reported an unhealthy container.",
            })
        elif status not in ("running", "exited"):
            severity = "medium"
            signals.append({
                "type": "unknown_status",
                "evidence": f"Saved status is {status!r}.",
            })

        if isinstance(restart_count, int) and restart_count > 0:
            restart_severity = "medium" if restart_count >= 3 else "low"
            if severity_order[restart_severity] > severity_order[severity]:
                severity = restart_severity
            signals.append({
                "type": "restarts_observed",
                "evidence": f"Saved restart count is {restart_count}.",
            })

        record = {
            "container": evidence.get("container", item.get("container")),
            "container_id": container_id,
            "status": status,
            "health": health,
            "exit_code": exit_code,
            "restart_count": restart_count,
            "project": project,
            "service": service,
            "collected_at": evidence.get("collected_at", item.get("collected_at")),
            "severity": severity,
            "signals": signals,
            "possible_relationships": [],
        }
        results.append(record)

        if project:
            projects[project].append(record)

    # Sharing a Compose project is a contextual relationship, not proof of dependency.
    for project, members in projects.items():
        if len(members) < 2:
            continue

        affected = [member for member in members if member["signals"]]
        if not affected:
            continue

        for member in members:
            for other in affected:
                if other["container_id"] == member["container_id"]:
                    continue
                member["possible_relationships"].append({
                    "container": other["container"],
                    "container_id": other["container_id"],
                    "relationship": "same_compose_project",
                    "evidence": (
                        f"Both containers belong to Docker Compose project "
                        f"{project!r}; this does not establish a dependency or cause."
                    ),
                })

    issue_count = sum(bool(record["signals"]) for record in results)

    return {
        "correlation_type": "deterministic_saved_evidence",
        "container_count": len(results),
        "containers_with_signals": issue_count,
        "containers": results,
        "limitations": [
            "Results use saved evidence, not live measurements.",
            "A shared Compose project does not prove a dependency relationship.",
            "Temporal proximity and co-occurrence do not prove causation.",
            "Missing labels or timestamps can limit correlation.",
            "No container, service, or infrastructure changes are performed.",
        ],
    }
