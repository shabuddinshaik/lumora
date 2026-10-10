import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="Lumora Read-Only Docker Diagnostics",
    version="0.2.0",
)

EVIDENCE_DIR = Path("/evidence")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_TARGETS = {
    "healthy": "healthy.json",
    "failing": "failing.json",
}


def read_json(filename):
    path = EVIDENCE_DIR / filename

    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Evidence snapshot has not been collected")
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Evidence snapshot is unavailable or invalid")


@app.get("/host/ssh")
def host_ssh_diagnostics():
    # Fixed filename only: no user-controlled paths or host command execution.
    return read_json("host-ssh.json")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "lumora-diagnostics-collector"}


@app.get("/containers")
def list_allowed_containers():
    # Preserve the existing response field for legacy clients.
    return {"allowed_targets": list(ALLOWED_TARGETS.keys())}


@app.get("/containers/{target}/diagnostics")
def container_diagnostics(target: str):
    filename = ALLOWED_TARGETS.get(target)
    if filename is None:
        raise HTTPException(status_code=404, detail="Container target is not allowlisted")
    return read_json(filename)


@app.get("/inventory")
def container_inventory():
    return read_json("inventory.json")


@app.get("/inventory/{container_id}")
def container_inventory_detail(container_id: str):
    if not CONTAINER_ID_RE.fullmatch(container_id):
        raise HTTPException(status_code=400, detail="Invalid container ID")

    inventory = read_json("inventory.json")
    known_ids = {item.get("id") for item in inventory.get("containers", [])}

    if container_id not in known_ids:
        raise HTTPException(status_code=404, detail="Container not found in the latest inventory")

    return read_json(f"container-{container_id}.json")
