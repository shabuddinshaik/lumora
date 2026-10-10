
#!/usr/bin/env bash

# Lumora diagnostics directory migration.
# Usage:
#   bash migrate-docker-lab.sh check
#   bash migrate-docker-lab.sh migrate

set -u

HOME_DIR="$HOME"
LUMORA_DIR="$HOME_DIR/lumora"
SOURCE="$HOME_DIR/lumora-docker-lab"
TARGET="$LUMORA_DIR/docker-lab"
BACKUP_DIR="$HOME_DIR/lumora-migration-backups/20261010T075251Z"
SERVICE="/etc/systemd/system/lumora-evidence-collector.service"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

check() {
  local failed=0

  [[ -f "$LUMORA_DIR/deploy.sh" ]] || { echo "Missing deploy.sh"; failed=1; }
  [[ -f "$SOURCE/collect_evidence.py" ]] || { echo "Missing source collector"; failed=1; }
  [[ -f "$SOURCE/compose.collector.yaml" ]] || { echo "Missing source Compose file"; failed=1; }
  [[ -d "$SOURCE/evidence" ]] || { echo "Missing source evidence directory"; failed=1; }
  [[ -d "$TARGET" ]] || { echo "Missing target directory"; failed=1; }

  if [[ -d "$TARGET" ]] && find "$TARGET" -mindepth 1 -print -quit | grep -q .; then
    echo "Target is not empty; refusing to overwrite it."
    failed=1
  fi

  if [[ -d "$SOURCE/evidence" ]]; then
    printf 'Source evidence files: '
    find "$SOURCE/evidence" -maxdepth 1 -type f | wc -l
  fi

  printf 'Collector health: '
  curl -fsS --max-time 5 http://localhost:8081/health || failed=1
  printf '\n'

  printf 'Evidence timer: '
  systemctl is-active lumora-evidence-collector.timer || failed=1

  [[ -f "$BACKUP_DIR/deploy.sh" ]] || { echo "Missing deploy backup"; failed=1; }
  [[ -f "$BACKUP_DIR/lumora-evidence-collector.service" ]] || {
    echo "Missing service backup"; failed=1;
  }

  if (( failed )); then
    echo "Preflight FAILED. Nothing was moved."
    return 1
  fi

  echo "Preflight PASSED. No files were changed."
}

migrate() {
  check || return 1

  echo
  echo "Migration will briefly stop only the diagnostics collector."
  echo "The main Lumora frontend, backend and PostgreSQL will not be restarted."
  read -r -p "Type MIGRATE to continue: " answer
  [[ "$answer" == "MIGRATE" ]] || { echo "Cancelled."; return 1; }

  echo "Stopping diagnostics collector..."
  docker compose -f "$SOURCE/compose.collector.yaml" stop lumora-diagnostics || {
    echo "Could not stop collector; source files remain in place."
    return 1
  }

  echo "Moving source files..."
  if ! mv "$SOURCE/." "$TARGET/"; then
    echo "Move failed. Do not delete either directory; inspect both before retrying."
    return 1
  fi

  echo "Updating deployment path..."
  if ! sed -i \
    's|${LUMORA_LAB_DIR:-$HOME/lumora-docker-lab}|${LUMORA_LAB_DIR:-$HOME/lumora/docker-lab}|' \
    "$LUMORA_DIR/deploy.sh"; then
    echo "Could not update deploy.sh. Files are at $TARGET; inspect before continuing."
    return 1
  fi

  echo "Updating systemd service paths..."
  if ! sudo sed -i \
    's|/home/mr_shabuddinshaik/lumora-docker-lab|/home/mr_shabuddinshaik/lumora/docker-lab|g' \
    "$SERVICE"; then
    echo "Could not update systemd service. Files are at $TARGET; inspect before continuing."
    return 1
  fi

  sudo systemctl daemon-reload || {
    echo "systemd reload failed. Inspect service before restarting collector."
    return 1
  }

  echo "Validating new Compose configuration..."
  docker compose -f "$TARGET/compose.collector.yaml" config -q || {
    echo "Compose validation failed. Inspect configuration before continuing."
    return 1
  }

  echo "Starting diagnostics collector at new path..."
  docker compose -f "$TARGET/compose.collector.yaml" up -d --build lumora-diagnostics || {
    echo "Collector start failed. Do not delete the target directory; inspect logs."
    return 1
  }

  echo "Running one evidence collection..."
  (
    cd "$TARGET" &&
    /usr/bin/python3 collect_evidence.py
  ) || {
    echo "Evidence collection failed. Inspect collector logs and permissions."
    return 1
  }

  echo "Verifying service and health..."
  systemctl is-active lumora-evidence-collector.timer || return 1
  curl -fsS --max-time 5 http://localhost:8081/health || return 1

  echo
  echo "Migration checks passed."
  echo "Source path: $SOURCE"
  echo "Target path: $TARGET"
  echo "Keep the old source directory only if it is empty; inspect before cleanup."
}

case "${1:-check}" in
  check) check ;;
  migrate) migrate ;;
  *)
    echo "Usage: bash migrate-docker-lab.sh [check|migrate]"
    exit 2
    ;;
esac

