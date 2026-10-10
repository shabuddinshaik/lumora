#!/usr/bin/env bash
set -Eeuo pipefail

LUMORA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="${LUMORA_LAB_DIR:-$LUMORA_DIR/docker-lab}"

ENVIRONMENT="production"
TARGET="all"

fail() {
  echo "ERROR: $*" >&2
  return 1
}

usage() {
  cat <<'HELP'
Usage:
  ./deploy.sh [--env production|staging|development]
              [--target app|diagnostics|all]

Examples:
  ./deploy.sh
  ./deploy.sh --env production --target app
  ./deploy.sh --env production --target diagnostics
  ./deploy.sh --env development --target app
  ./deploy.sh --env staging --target app

Production is the default environment.
Development/staging diagnostics are intentionally blocked until
separate evidence collection is implemented.
HELP
}

while (($#)); do
  case "$1" in
    --env)
      [[ $# -ge 2 ]] || { usage; fail "--env needs a value."; }
      ENVIRONMENT="$2"
      shift 2
      ;;
    --target)
      [[ $# -ge 2 ]] || { usage; fail "--target needs a value."; }
      TARGET="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      fail "Unknown argument: $1"
      ;;
  esac
done

case "$ENVIRONMENT" in
  production|staging|development) ;;
  *) fail "Environment must be production, staging, or development." ;;
esac

case "$TARGET" in
  app|diagnostics|all) ;;
  *) fail "Target must be app, diagnostics, or all." ;;
esac

command -v docker >/dev/null || fail "Docker is not installed."
command -v curl >/dev/null || fail "curl is not installed."
command -v python3 >/dev/null || fail "Python 3 is not installed."
docker compose version >/dev/null || fail "Docker Compose is unavailable."

APP_COMPOSE="$LUMORA_DIR/docker-compose.yml"
[[ -f "$APP_COMPOSE" ]] || fail "Main Compose file is missing."

echo "Environment: $ENVIRONMENT"
echo "Target:      $TARGET"

if [[ "$ENVIRONMENT" != "production" ]]; then
  # This first version deliberately limits non-production to the app.
  [[ "$TARGET" == "app" ]] ||
    fail "Non-production diagnostics/all are blocked until isolated evidence collection is implemented."

  ENV_FILE="$LUMORA_DIR/deploy/environments/$ENVIRONMENT.env"
  OVERRIDE="$LUMORA_DIR/deploy/compose/$ENVIRONMENT.yaml"

  [[ -f "$ENV_FILE" ]] ||
    fail "Missing $ENV_FILE. Copy its .env.example template and set unique credentials first."
  [[ -f "$OVERRIDE" ]] || fail "Missing Compose override: $OVERRIDE"

  # Validate credentials without printing their values.
  python3 - "$ENV_FILE" "$ENVIRONMENT" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
env_name = sys.argv[2]
values = {}

for line in path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip().strip("'\"")

required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
missing = [key for key in required if not values.get(key)]
if missing:
    sys.exit("ERROR: Missing required database settings: " + ", ".join(missing))

for key in required:
    value = values[key].lower()
    if "replace_with" in value or value in {"changeme", "change_me", "password"}:
        sys.exit("ERROR: Replace placeholder credentials in the environment file.")

if values["POSTGRES_DB"] in {"lumora", "lumora_development", "lumora_staging"}:
    expected = "lumora_" + env_name
    if values["POSTGRES_DB"] != expected:
        sys.exit("ERROR: Database name does not match this environment.")

if values["POSTGRES_USER"] == "lumora":
    sys.exit("ERROR: Use a dedicated non-production database user.")

print("Environment file validation passed; credentials were not displayed.")
PY

  # Keep runtime uploads separate for each environment.
  mkdir -p "$LUMORA_DIR/deploy/runtime/$ENVIRONMENT/uploads"
  chmod 750 "$LUMORA_DIR/deploy/runtime/$ENVIRONMENT/uploads"

  PROJECT="lumora-$ENVIRONMENT"

  echo "== Validate $ENVIRONMENT Compose configuration =="
  docker compose \
    --project-directory "$LUMORA_DIR" \
    --env-file "$ENV_FILE" \
    -p "$PROJECT" \
    -f "$APP_COMPOSE" \
    -f "$OVERRIDE" config -q

  echo "== Deploy $ENVIRONMENT application only =="
  docker compose \
    --project-directory "$LUMORA_DIR" \
    --env-file "$ENV_FILE" \
    -p "$PROJECT" \
    -f "$APP_COMPOSE" \
    -f "$OVERRIDE" up -d

  BACKEND_PORT="$(python3 - "$ENV_FILE" "$ENVIRONMENT" <<'PY'
import sys
from pathlib import Path
values = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip("'\"")
default = "8001" if sys.argv[2] == "development" else "8002"
print(values.get("BACKEND_PORT", default))
PY
)"

  echo "== Verify $ENVIRONMENT backend health =="
  curl --retry 10 --retry-connrefused --retry-delay 2 \
    --fail --silent --show-error \
    "http://127.0.0.1:${BACKEND_PORT}/health"
  echo
  echo "$ENVIRONMENT application deployment checks completed."
  exit 0
fi

# Production retains the existing project identity and resources.
docker compose --project-directory "$LUMORA_DIR" \
  -p lumora -f "$APP_COMPOSE" config -q

if [[ "$TARGET" == "app" ]]; then
  echo "== Build production application services =="
  docker compose --project-directory "$LUMORA_DIR" \
    -p lumora -f "$APP_COMPOSE" build backend frontend

  echo "== Update production application services only =="
  docker compose --project-directory "$LUMORA_DIR" \
    -p lumora -f "$APP_COMPOSE" up -d --no-deps backend frontend

  echo "== Verify production backend health =="
  curl --retry 10 --retry-connrefused --retry-delay 2 \
    --fail --silent --show-error http://localhost:8000/health
  echo

  echo "== Verify production frontend =="
  curl --retry 10 --retry-connrefused --retry-delay 2 \
    --fail --silent --show-error -o /dev/null \
    -w "Frontend HTTP %{http_code}\\n" http://localhost/

  echo "Production application checks completed."
  exit 0
fi

[[ -f "$LAB_DIR/compose.collector.yaml" ]] ||
  fail "Collector Compose file missing at $LAB_DIR."
[[ -f "$LAB_DIR/collect_evidence.py" ]] ||
  fail "Evidence collection script missing at $LAB_DIR."
[[ -d "$LAB_DIR/collector" ]] ||
  fail "Collector source directory missing at $LAB_DIR."

if [[ "$TARGET" == "diagnostics" ]]; then
  docker network inspect lumora_default >/dev/null ||
    fail "Production network lumora_default is missing. Deploy the production app first."
fi

GROUP_NAME="lumora-evidence"
EVIDENCE_DIR="$LAB_DIR/evidence"

if ! getent group "$GROUP_NAME" >/dev/null; then
  echo "Creating evidence group..."
  sudo groupadd --system "$GROUP_NAME"
fi

GROUP_ENTRY="$(getent group "$GROUP_NAME")"
EVIDENCE_GID="$(printf '%s' "$GROUP_ENTRY" | cut -d: -f3)"
export LUMORA_EVIDENCE_GID="$EVIDENCE_GID"

mkdir -p "$EVIDENCE_DIR"
sudo chown "$(id -u):$EVIDENCE_GID" "$EVIDENCE_DIR"
chmod 2750 "$EVIDENCE_DIR"
find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec sudo chgrp "$GROUP_NAME" {} +
find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec chmod 640 {} +

docker compose --project-directory "$LAB_DIR" \
  -p lumora -f "$LAB_DIR/compose.collector.yaml" config -q
python3 -m py_compile "$LAB_DIR/collect_evidence.py"

if [[ "$TARGET" == "all" ]]; then
  echo "== Deploy production application =="
  docker compose --project-directory "$LUMORA_DIR" \
    -p lumora -f "$APP_COMPOSE" up -d
fi

echo "== Deploy production diagnostics collector =="
docker compose --project-directory "$LAB_DIR" \
  -p lumora -f "$LAB_DIR/compose.collector.yaml" \
  up -d --build lumora-diagnostics

echo "== Collect initial evidence =="
(cd "$LAB_DIR" && python3 collect_evidence.py)

find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec sudo chgrp "$GROUP_NAME" {} +
find "$EVIDENCE_DIR" -maxdepth 1 -type f -exec chmod 640 {} +

docker inspect lumora-diagnostics \
  --format '{{json .NetworkSettings.Networks}}' |
  grep -q '"lumora_default"' ||
  fail "Collector is not connected to lumora_default."

echo "== Verify production diagnostics health =="
curl --retry 10 --retry-connrefused --retry-delay 2 \
  --fail --silent --show-error http://localhost:8081/health
echo

if [[ "$TARGET" == "all" ]]; then
  echo "== Verify production backend health =="
  curl --retry 10 --retry-connrefused --retry-delay 2 \
    --fail --silent --show-error http://localhost:8000/health
  echo

  echo "== Verify production inventory API =="
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
fi

echo "== Verify evidence permissions =="
stat -c '%A %a %U %G %n' "$EVIDENCE_DIR"
find "$EVIDENCE_DIR" -maxdepth 1 -type f \
  -name inventory.json -exec stat -c '%A %a %U %G %n' {} +

echo "Deployment checks completed successfully."
