import subprocess

WINDOW_MINUTES = 30
RECENT_LIMIT = 10

PATTERNS = {
    "resource_pressure": (
        "out of memory",
        "oom-kill",
        "killed process",
        "memory cgroup out of memory",
        "blocked for more than",
        "hung task",
    ),
    "io_network_or_panic": (
        "i/o error",
        "buffer i/o error",
        "blk_update_request",
        "netdev watchdog",
        "kernel panic",
        "general protection fault",
        "bug:",
        "oops:",
    ),
}


def collect_kernel_events():
    result = subprocess.run(
        [
            "journalctl",
            "-k",
            "--since",
            f"{WINDOW_MINUTES} minutes ago",
            "--no-pager",
            "-o",
            "short-iso",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )

    lines = result.stdout.splitlines()
    evidence = {}

    for category, patterns in PATTERNS.items():
        matches = [
            line for line in lines
            if any(pattern in line.lower() for pattern in patterns)
        ]

        evidence[category] = {
            "count": len(matches),
            "recent_events": [
                {
                    "timestamp": line.split(maxsplit=1)[0],
                    "event": line,
                }
                for line in matches[-RECENT_LIMIT:]
            ],
        }

    return evidence


if __name__ == "__main__":
    import json

    try:
        print(json.dumps(collect_kernel_events(), indent=2))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"Kernel evidence collection failed: {exc}")
        raise
