#!/usr/bin/env python3

import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from host_kernel_collector import collect_kernel_events

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
OUTPUT = EVIDENCE_DIR / "host-ssh.json"
WINDOW_MINUTES = 30
RECENT_LIMIT = 10

LIMITATIONS = [
    "Only recent journal events matching known patterns are counted.",
    "Unauthenticated connection endings are separated from other disconnect events.",
    "A disconnect event does not establish whether the SSH client, network, or server caused it.",
    "SSH authentication failures do not establish the cause of a disconnect.",
    "A snapshot cannot prove root cause or rule out events absent from the journal.",
    "Recent disconnect events may include sessions other than the user's session.",
    "Counts are based on journal messages and may not represent unique users or sessions.",
]

def now():
    return datetime.now(timezone.utc).isoformat()

def run_readonly(args, timeout=20):
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    ).stdout

def collect_journal():
    # Use the service unit, which is accessible to the current account.
    return run_readonly([
        "journalctl",
        "-u", "ssh.service",
        "--since", f"{WINDOW_MINUTES} minutes ago",
        "--no-pager",
        "-o", "short-iso",
    ])

def classify(line):
    lower = line.lower()

    # Authentication success must be explicitly recorded.
    if re.search(
        r"\baccepted\s+(password|publickey|keyboard-interactive|hostbased)\b",
        lower,
    ):
        return "authentication_success", "SSH authentication accepted"

    if "invalid user " in lower:
        return "authentication_failure", "SSH authentication attempt for invalid user"

    if (
        re.search(r"\bfailed\s+(password|publickey|keyboard-interactive)\b", lower)
        or "authentication failure" in lower
        or "maximum authentication attempts exceeded" in lower
    ):
        return "authentication_failure", "SSH authentication failed"

    if (
        "[preauth]" in lower
        or "before authentication" in lower
        or "unauthenticated connection" in lower
    ):
        return "preauth_disconnect", "Unauthenticated connection ended"

    # A generic connection ending does not prove authentication succeeded.
    if "disconnected from" in lower or "connection closed" in lower:
        return "unclassified_disconnect", "Connection ended; authentication state unknown"

    return None

def parse_timestamp(line):
    # journalctl -o short-iso starts with an ISO-like timestamp.
    match = re.match(r"^(\d{4}-\d{2}-\d{2}T\S+)", line)
    return match.group(1) if match else None

def host_summary(args):
    try:
        return run_readonly(args, timeout=10).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

def atomic_write(data):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # Backups are created explicitly before the first live refresh, not per run.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=EVIDENCE_DIR,
        prefix=".host-ssh-",
        suffix=".tmp",
        delete=False,
    ) as temp:
        json.dump(data, temp, indent=2)
        temp.write("\n")
        temp_path = Path(temp.name)

    temp_path.chmod(0o640)
    temp_path.replace(OUTPUT)

def main():
    # Fail closed: do not replace existing evidence if journal collection fails.
    journal = collect_journal()

    categories = {
        "authentication_success": [],
        "authentication_failure": [],
        "preauth_disconnect": [],
        "established_disconnect": [],
        "unclassified_disconnect": [],
    }

    for line in journal.splitlines():
        result = classify(line)
        if result is None:
            continue

        category, description = result
        categories[category].append({
            "timestamp": parse_timestamp(line),
            "event": description,
        })

    ssh = {}
    for name, events in categories.items():
        ssh[name] = {
            "count": len(events),
            "recent_events": events[-RECENT_LIMIT:],
        }

    data = {
        "collected_at": now(),
        "source": "read-only host SSH journal",
        "window_minutes": WINDOW_MINUTES,
        "uptime_summary": host_summary(["uptime"]),
        "memory_summary": host_summary(["free", "-h"]),
        "root_disk_summary": host_summary(["df", "-h", "/"]),
        "ssh": ssh,
        # Collect real kernel journal matches; do not fabricate zero counts.
        "kernel": collect_kernel_events(),
        "limitations": LIMITATIONS,
    }

    atomic_write(data)
    print(
        f"SSH evidence refreshed: window={WINDOW_MINUTES}m, "
        + ", ".join(f"{key}={value['count']}" for key, value in ssh.items())
    )

if __name__ == "__main__":
    main()
