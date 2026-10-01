#!/usr/bin/env bash
# Safe production deploy for the Arrow Frappe app.
# Invoked by GitHub Actions only after the checked-out commit is verified.

set -euo pipefail

EXPECTED_SHA="${1:?Usage: deploy-arrow.sh <expected-git-sha>}"
BENCH_DIR="/home/frappe/frappe-bench"
APP_DIR="$BENCH_DIR/apps/arrow"
APP_NAME="arrow"
DEMO_SITE="demo.airbit.biz"
LOG_DIR="/home/frappe/deploy-logs"
LOG_FILE="$LOG_DIR/deploy-arrow-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

cd "$APP_DIR"
ACTUAL_SHA="$(git rev-parse HEAD)"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  echo "REFUSING: checked-out commit ($ACTUAL_SHA) does not match requested commit ($EXPECTED_SHA)."
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "REFUSING: production app repository has local changes. Resolve them through Git first."
  git status --short
  exit 1
fi

mapfile -t TARGET_SITES < <(
  cd "$BENCH_DIR"
  for config in sites/*/site_config.json; do
    [[ -f "$config" ]] || continue
    site="$(basename "$(dirname "$config")")"
    [[ "$site" == "$DEMO_SITE" ]] && continue
    if bench --site "$site" list-apps 2>/dev/null | awk '{print $1}' | grep -Fxq "$APP_NAME"; then
      printf '%s\n' "$site"
    fi
  done
)

if (( ${#TARGET_SITES[@]} == 0 )); then
  echo "REFUSING: no non-demo site has the '$APP_NAME' application installed."
  exit 1
fi

echo "============================================================"
echo "Arrow deployment: $EXPECTED_SHA"
echo "Target sites: ${TARGET_SITES[*]}"
echo "Started: $(date --iso-8601=seconds)"
echo "============================================================"

cd "$BENCH_DIR"
for site in "${TARGET_SITES[@]}"; do
  echo "--- Deploying $APP_NAME to $site ---"
  bench --site "$site" backup --with-files
  bench --site "$site" migrate
  bench --site "$site" clear-cache
  bench --site "$site" clear-website-cache
  echo "--- Completed $site ---"
done

echo "No shared bench/Gunicorn restart was performed by this workflow."
echo "Completed: $(date --iso-8601=seconds)"
echo "Log: $LOG_FILE"
