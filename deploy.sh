#!/usr/bin/env bash
set -Eeuo pipefail

LUMORA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="${LUMORA_LAB_DIR:-$HOME/lumora/docker-lab}"
EVIDENCE_DIR="$LAB_DIR/evidence"
GROUP_NAME="lumora-evidence"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

echo "== Lumora deployment =="
echo "Application: $LUMORA_DIR"
echo "Diagnostics: $LAB_DIR"

command -v docker >/dev/null || fail "Docker is not installed."
command -v curl >/dev/null || fail "curl is not installed."
command -v python3 >/dev/null || fail "Python 3 is not installed."
docker compose version >/dev/null || fail "Docker Compose is unavailable."

[[ -f "$LUMORA_DIR/docker-compose.yml" ]] || fail "Lumora Compose file missing."
[[ -f "$LAB_DIR/compose.collector.yaml" ]] || fail "Collector Compose file missing."
[[ -f "$LAB_DIR/collect_evidence.py" ]] || fail "Evidence collection script missing."
[[ -d "$LAB_DIR/collector" ]] || fail "Collector source directory missing."

# Bootstrap the evidence group when running on a new server.
if ! getent group "$GROUP_NAME" >/dev/null; then
  echo "Creating evidence group..."
  sudo groupadd --system "$GROUP_NAME"
fi

GROUP_ENTRY="$(getent group "$GROUP_NAME")"
EVIDENCE_GID="$(printf '%s' "$GROUP_ENTRY" | cut -d: -f3)"
export LUMORA_EVIDENCE_GID="$EVIDENCE_GID"

# Prepare restricted evidence storage.
mkdir -p "$EVIDENCE_DIR"
sudo chown "$(id -u):$EVIDENCE_GID" "$EVIDENCE_DIR"
chmod 2750 "$EVIDENCE_DIR"

# Normalize existing evidence without making it world-readable.
find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec sudo chgrp "$GROUP_NAME" {} +
find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec chmod 640 {} +

echo "Evidence group: $GROUP_NAME (GID $EVIDENCE_GID)"

echo "== Validate configurations =="
docker compose -f "$LUMORA_DIR/docker-compose.yml" config -q
docker compose -f "$LAB_DIR/compose.collector.yaml" config -q
python3 -m py_compile "$LAB_DIR/collect_evidence.py"

echo "== Start Lumora application =="
docker compose -f "$LUMORA_DIR/docker-compose.yml" up -d

echo "== Start diagnostics collector =="
docker compose -f "$LAB_DIR/compose.collector.yaml" up -d --build lumora-diagnostics

echo "== Collect initial evidence =="
(
  cd "$LAB_DIR"
  python3 collect_evidence.py
)

echo "== Normalize evidence permissions =="
find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec sudo chgrp "$GROUP_NAME" {} +
find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec chmod 640 {} +

echo "== Verify network attachment =="
docker inspect lumora-diagnostics \
  --format '{{json .NetworkSettings.Networks}}' |
  grep -q '"lumora_default"' ||
  fail "Collector is not connected to lumora_default."

echo "== Verify collector health =="
curl --retry 10 --retry-connrefused --retry-delay 2 \
  --fail --silent --show-error http://localhost:8081/health
echo

echo "== Verify backend health =="
curl --retry 10 --retry-connrefused --retry-delay 2 \
  --fail --silent --show-error http://localhost:8000/health
echo

echo "== Verify inventory API =="
curl --fail --silent --show-error \
  http://localhost:8000/api/v1/devops/containers |
  python3 -c '
import json, sys
d = json.load(sys.stdin)
print("Discovered:", d["total_discovered"])
print("Collected:", d["total_collected"])
print("Failed:", d["total_failed"])
if d["total_failed"] != 0:
    raise SystemExit("Evidence collection failures detected.")
'

echo "== Verify evidence permissions =="
stat -c '%A %a %U %G %n' "$EVIDENCE_DIR"
find "$EVIDENCE_DIR" -maxdepth 1 -type f \
  -name inventory.json -exec stat -c '%A %a %U %G %n' {} +

echo "Deployment checks completed successfully."
