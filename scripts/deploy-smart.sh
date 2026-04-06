#!/usr/bin/env bash
# scripts/deploy-smart.sh — Mac → SSH smart deploy (4GB RAM VPS: stop containers before docker build).
#
# Usage:
#   bash scripts/deploy-smart.sh [--skip-sync] [--skip-build] [--rollback]
#
# Optional overrides (environment or .env.deploy in repo root):
#   SERVER, REMOTE_DIR, REPO_DIR, IMAGE, CONTAINER, NETWORK, EXPECTED_VERSION, SYNC_SCRIPT
#
set -euo pipefail

SERVER="${SERVER:-root@64.227.146.129}"
REMOTE_DIR="${REMOTE_DIR:-/opt/papa-ecosystem}"
REPO_DIR="${REPO_DIR:-/tmp/papa-lang-src}"
NETWORK="${NETWORK:-papa-ecosystem_papa-network}"
IMAGE="${IMAGE:-papa-ecosystem-frontend:latest}"
BACKUP_TAG="${BACKUP_TAG:-papa-ecosystem-frontend:deploy-backup}"
CONTAINER="${CONTAINER:-papa-frontend-prod}"
EXPECTED_VERSION="${EXPECTED_VERSION:-1.5.1}"
HEALTH_PORT="${HEALTH_PORT:-3000}"
SYNC_SCRIPT="${SYNC_SCRIPT:-}"

# Container dependency order (start in this order; stop in reverse)
CONTAINERS_INFRA=(
  "papa-devops-unified-postgres-1"
  "papa-redis-prod"
)
CONTAINERS_SERVICES=(
  "papa-ecosystem-new-litellm-1"
  "papa-api-prod"
)
CONTAINERS_FRONTEND=(
  "papa-frontend-prod"
)

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/deploy-$(date +%Y%m%d-%H%M%S).log"

DEPLOY_START_TS="$(date +%s)"
CURRENT_STEP=0
TOTAL_STEPS=7
SKIP_SYNC=0
SKIP_BUILD=0
ROLLBACK_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --skip-sync)  SKIP_SYNC=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --rollback)   ROLLBACK_ONLY=1 ;;
    *) ;; esac
done

# Optional repo-level deploy overrides (no secrets required; SSH keys only)
ENV_DEPLOY="${REPO_ROOT}/.env.deploy"
if [ -f "$ENV_DEPLOY" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$ENV_DEPLOY"
  set +a
fi

# Server paths only — verified on host during sync (see preflight).
if [ -z "$SYNC_SCRIPT" ]; then
  SYNC_SCRIPT="${REPO_DIR}/scripts/sync-to-papa-app.sh"
fi

log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
ok()  { echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"; }
err() { echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"; }
warn(){ echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"; }

step() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  log "[$CURRENT_STEP/$TOTAL_STEPS] $1"
}

run_ssh() {
  ssh -o BatchMode=yes -o ConnectTimeout=15 "$SERVER" "$@"
}

# --- Remote helpers (heredocs pass SERVER-side paths safely) ---

remote_stop_ordered() {
  local -a rev=()
  local i
  for (( i=${#CONTAINERS_FRONTEND[@]}-1; i>=0; i-- )); do rev+=("${CONTAINERS_FRONTEND[i]}"); done
  for (( i=${#CONTAINERS_SERVICES[@]}-1; i>=0; i-- )); do rev+=("${CONTAINERS_SERVICES[i]}"); done
  for (( i=${#CONTAINERS_INFRA[@]}-1; i>=0; i-- )); do rev+=("${CONTAINERS_INFRA[i]}"); done
  local list
  list="$(printf '%s ' "${rev[@]}")"
  run_ssh "bash -c 'docker stop ${list} 2>/dev/null || true'"
}

remote_start_infra() {
  local list
  list="$(printf '%s ' "${CONTAINERS_INFRA[@]}")"
  run_ssh "bash -c 'set -e; for c in ${list}; do docker start \"\$c\" 2>/dev/null && echo started \"\$c\" || echo skip \"\$c\"; done'"
}

remote_start_services() {
  local list
  list="$(printf '%s ' "${CONTAINERS_SERVICES[@]}")"
  run_ssh "bash -c 'set -e; for c in ${list}; do docker start \"\$c\" 2>/dev/null && echo started \"\$c\" || echo skip \"\$c\"; done'"
}

remote_save_frontend_env() {
  run_ssh "bash -s" <<REMOTE
set -euo pipefail
CONTAINER="$(printf '%s' "$CONTAINER")"
REMOTE_DIR="$(printf '%s' "$REMOTE_DIR")"
if docker inspect "\$CONTAINER" >/dev/null 2>&1; then
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "\$CONTAINER" > /tmp/papa-deploy-frontend.env
elif [ -f "\$REMOTE_DIR/.env.production" ]; then
  cp "\$REMOTE_DIR/.env.production" /tmp/papa-deploy-frontend.env
elif [ -f "\$REMOTE_DIR/.env" ]; then
  cp "\$REMOTE_DIR/.env" /tmp/papa-deploy-frontend.env
else
  touch /tmp/papa-deploy-frontend.env
fi
REMOTE
}

remote_force_nextauth_app_url() {
  # Match ai-saas-platform/scripts/deploy-vps-docker.sh for papa-frontend-prod
  run_ssh "bash -s" <<'REMOTE'
set -euo pipefail
f=/tmp/papa-deploy-frontend.env
if [ -f "$f" ]; then
  grep -v '^NEXTAUTH_URL=' "$f" > "${f}.tmp" 2>/dev/null || true
  mv "${f}.tmp" "$f" 2>/dev/null || true
  echo "NEXTAUTH_URL=https://app.papa-ai.ae" >> "$f"
fi
REMOTE
}

remote_remove_frontend() {
  run_ssh "docker rm -f \"$CONTAINER\" 2>/dev/null || true"
}

remote_run_frontend() {
  run_ssh "bash -c 'set -e; docker run -d --name \"$CONTAINER\" --restart unless-stopped -p ${HEALTH_PORT}:3000 --env-file /tmp/papa-deploy-frontend.env --network \"$NETWORK\" \"$IMAGE\"'"
}

remote_tag_backup_as_latest() {
  run_ssh "docker image inspect \"$BACKUP_TAG\" >/dev/null 2>&1 && docker tag \"$BACKUP_TAG\" \"$IMAGE\" || { echo \"missing $BACKUP_TAG\"; exit 1; }"
}

remote_backup_current_image() {
  run_ssh "bash -c 'set -e; if docker image inspect \"$IMAGE\" >/dev/null 2>&1; then docker tag \"$IMAGE\" \"$BACKUP_TAG\"; echo tagged_backup; else echo no_image_to_backup; fi'"
}

check_disk() {
  local free_gb
  free_gb="$(run_ssh "df / --output=avail -BG 2>/dev/null | tail -1 | tr -cd '0-9' || echo 0")"
  if [ -z "$free_gb" ] || [ "$free_gb" -lt 5 ] 2>/dev/null; then
    err "Disk check: need 5GB+ free on / (parsed: ${free_gb:-0}GB)"
    return 1
  fi
  ok "Disk space: ${free_gb}GB free"
}

check_memory() {
  local free_mb
  free_mb="$(run_ssh "free -m 2>/dev/null | awk \"/^Mem:/{print \\\$7}\" || echo 0")"
  log "Available RAM: ${free_mb}MB"
  if [ "${free_mb:-0}" -lt 2500 ] 2>/dev/null; then
    warn "Low RAM: ${free_mb}MB (target 2500MB+ for build with containers stopped)"
    return 1
  fi
  ok "RAM: ${free_mb}MB available (approx)"
}

check_health() {
  local health
  health="$(run_ssh "curl -sf \"http://127.0.0.1:${HEALTH_PORT}/api/health\"" 2>/dev/null || true)"
  if [ -z "$health" ]; then
    err "Health endpoint not responding (port ${HEALTH_PORT})"
    return 1
  fi
  local py_out
  py_out="$(echo "$health" | python3 -c "
import sys, json, re
try:
    r = json.load(sys.stdin)
except Exception as e:
    print('ERROR:json:' + str(e))
    sys.exit(0)
d = r.get('data', r)
ok = d.get('ok')
ver = d.get('version', 'unknown')
st = d.get('status', '')
sub = d.get('subsystems', {}) or {}
lang = sub.get('papa-lang', {}) or {}
detail = str(lang.get('detail', ''))
mods = ''
m = re.search(r'(\\d+)\\s*modules', detail)
if m:
    mods = m.group(1)
critical_bad = []
for name, meta in sub.items():
    if not isinstance(meta, dict):
        continue
    s = meta.get('status', '')
    if name in ('papa-db', 'papa-lang') and s == 'unhealthy':
        critical_bad.append(name)
if critical_bad:
    print('ERROR:critical:' + ','.join(critical_bad))
elif str(ok).lower() not in ('true', '1'):
    print('ERROR:badok')
else:
    print('OK|%s|%s|%s|%s' % (ver, st, mods, detail))
")"

  case "$py_out" in
    ERROR:critical:*)
      err "Health check failed (${py_out#ERROR:critical:})"
      return 1
      ;;
    ERROR:badok)
      err "Health check failed: ok flag false inside payload"
      return 1
      ;;
    ERROR:json:*)
      err "Health JSON parse failed: ${py_out#ERROR:json:}"
      return 1
      ;;
    OK\|*) ;;
    *)
      err "Health check: unexpected parser output: ${py_out:-empty}"
      return 1
      ;;
  esac

  local tail="${py_out#OK|}"
  local hv st_g mods _detail
  hv="${tail%%|*}"
  tail="${tail#*|}"
  st_g="${tail%%|*}"
  tail="${tail#*|}"
  mods="${tail%%|*}"
  if [ "$st_g" = "degraded" ]; then
    warn "Overall health status is degraded (see subsystem verification step)"
  fi
  if [ "$hv" != "$EXPECTED_VERSION" ]; then
    warn "Version is $hv (expected $EXPECTED_VERSION)"
  else
    ok "Version matches expected: $EXPECTED_VERSION"
  fi
  ok "Health: OK | version=$hv | papa-lang modules (parsed): ${mods:-?}"
  return 0
}

print_subsystems() {
  local health
  health="$(run_ssh "curl -sf \"http://127.0.0.1:${HEALTH_PORT}/api/health\"" 2>/dev/null || true)"
  [ -z "$health" ] && { err "No health body for subsystem dump"; return 1; }
  echo "$health" | python3 -c "
import sys, json
r = json.load(sys.stdin)
d = r.get('data', r)
sub = d.get('subsystems', {}) or {}
for name in sorted(sub.keys()):
    m = sub[name]
    if isinstance(m, dict):
        st = m.get('status', '')
        ms = m.get('ms', '')
        det = m.get('detail', '')
        extra = ' (%sms)' % ms if ms != '' else ''
        detpart = (' - ' + str(det)) if det else ''
        print('%s: %s%s%s' % (name, st, extra, detpart))
    else:
        print('%s: %s' % (name, m))
" | while IFS= read -r line; do ok "$line"; done
}

rollback_frontend() {
  err "Rolling back: retag $BACKUP_TAG → $IMAGE and recreate $CONTAINER"
  remote_start_infra || true
  sleep 5
  remote_start_services || true
  sleep 3
  remote_remove_frontend || true
  remote_tag_backup_as_latest || { err "Rollback tag failed"; return 1; }
  remote_force_nextauth_app_url || true
  remote_run_frontend || { err "Rollback docker run failed"; return 1; }
  sleep 15
  if ! check_health; then
    err "Rollback finished but health still failing — manual intervention required"
    return 1
  fi
  return 0
}

recover_stack_after_failed_build() {
  warn "Build failed — bringing stack back (image :latest unchanged); recreating frontend container"
  remote_start_infra || true
  sleep 5
  remote_start_services || true
  sleep 3
  remote_force_nextauth_app_url || true
  remote_run_frontend || { err "Could not recreate frontend after failed build"; return 1; }
  sleep 15
  if ! check_health; then
    err "Health still failing after recover_stack — inspect VPS manually"
    return 1
  fi
  warn "Stack is back up on the previous image; deploy aborted"
  return 0
}

rollback_manual_only() {
  step "Rollback only ($BACKUP_TAG)"
  if ! run_ssh "docker image inspect \"$BACKUP_TAG\" >/dev/null 2>&1"; then
    err "No $BACKUP_TAG on server — cannot rollback"
    exit 1
  fi
  remote_save_frontend_env || true
  remote_force_nextauth_app_url || true
  remote_remove_frontend || true
  remote_tag_backup_as_latest
  remote_run_frontend
  sleep 15
  check_health || exit 1
  ok "Rollback complete"
  exit 0
}

# --- Main ---

if [ "$ROLLBACK_ONLY" -eq 1 ]; then
  rollback_manual_only
fi

step "Pre-flight checks"
if ! run_ssh "true"; then
  err "SSH connection failed ($SERVER)"
  exit 1
fi
ok "SSH connection OK"

check_disk || exit 1

nrun="$(run_ssh "docker ps -q 2>/dev/null | wc -l | tr -d '[:space:]'")"
ok "Containers currently running: ${nrun:-?}"

backup_line="$(remote_backup_current_image 2>&1 | tee -a "$LOG_FILE")"
if echo "$backup_line" | grep -q tagged_backup; then
  ok "Previous image tagged as $BACKUP_TAG"
else
  warn "No existing $IMAGE to backup (first deploy?)"
fi

step "Syncing repository → app (skip=$SKIP_SYNC)"
if [ "$SKIP_SYNC" -eq 0 ]; then
  if ! run_ssh "test -d \"$REPO_DIR\""; then
    err "REPO_DIR missing on server: $REPO_DIR"
    exit 1
  fi
  if ! run_ssh "test -f \"$SYNC_SCRIPT\""; then
    alt_sync="${REMOTE_DIR}/scripts/sync-to-papa-app.sh"
    if run_ssh "test -f \"$alt_sync\""; then
      warn "Using fallback sync script: $alt_sync"
      SYNC_SCRIPT="$alt_sync"
    else
      err "Sync script not found on server: $SYNC_SCRIPT (set SYNC_SCRIPT in .env.deploy)"
      exit 1
    fi
  fi
  log "Git pull in $REPO_DIR"
  run_ssh "bash -c 'set -e; cd \"$REPO_DIR\" && git pull origin main'" | tee -a "$LOG_FILE"
  log "Run sync: DEST=$REMOTE_DIR bash $SYNC_SCRIPT"
  run_ssh "bash -c 'set -e; export DEST=\"$REMOTE_DIR\"; bash \"$SYNC_SCRIPT\"'" | tee -a "$LOG_FILE"
  fcount="$(run_ssh "find \"$REMOTE_DIR\" -type f 2>/dev/null | wc -l | tr -d '[:space:]'")"
  ok "Files under $REMOTE_DIR: $fcount"
else
  warn "Skipped sync"
fi

step "Build (stop containers to free RAM) skip=$SKIP_BUILD"
BUILD_TIME=0
if [ "$SKIP_BUILD" -eq 0 ]; then
  remote_save_frontend_env
  remote_force_nextauth_app_url

  warn "Stopping containers (reverse dependency order)…"
  remote_stop_ordered
  ok "Stop issued for stack"

  remote_remove_frontend

  log "Docker prune (non-interactive)"
  run_ssh "docker system prune -f" | tee -a "$LOG_FILE" || true

  run_ssh "free -h" | tee -a "$LOG_FILE"
  check_memory || warn "Proceeding with build despite RAM warning"

  log "docker build in $REMOTE_DIR (requires several minutes)"
  BUILD_START="$(date +%s)"
  if ! run_ssh "bash -c 'set -e; cd \"$REMOTE_DIR\"; set -a; [ -f .env ] && . .env; [ -f .env.production ] && . .env.production; set +a; docker build -t \"$IMAGE\" -f Dockerfile --build-arg NEXTAUTH_SECRET=\"\${NEXTAUTH_SECRET:-build-placeholder}\" --build-arg DATABASE_URL=\"\${DATABASE_URL:-postgresql://build:build@localhost:5432/build}\" .'"; then
    BUILD_END="$(date +%s)"
    BUILD_TIME=$((BUILD_END - BUILD_START))
    err "Docker build failed after ${BUILD_TIME}s — restarting stack on previous image"
    recover_stack_after_failed_build || true
    exit 1
  fi
  BUILD_END="$(date +%s)"
  BUILD_TIME=$((BUILD_END - BUILD_START))
  log "Build completed in ${BUILD_TIME}s ($((BUILD_TIME / 60))m $((BUILD_TIME % 60))s)"
else
  warn "Skipped build"
fi

step "Starting containers"
remote_start_infra
sleep 5
remote_start_services
sleep 3

if [ "$SKIP_BUILD" -eq 1 ]; then
  if run_ssh "docker inspect \"$CONTAINER\" >/dev/null 2>&1"; then
    run_ssh "docker start \"$CONTAINER\""
    ok "Frontend container started (skip-build; existing container)"
  else
    warn "Frontend container missing — creating from saved env / .env.production"
    remote_save_frontend_env
    remote_force_nextauth_app_url
    remote_run_frontend
    ok "Frontend container created"
  fi
else
  remote_save_frontend_env
  remote_force_nextauth_app_url
  remote_remove_frontend
  remote_run_frontend
  ok "Frontend container (re)created"
fi

log "Wait for Next.js cold start (15s)"
sleep 15

step "Health check"
if ! check_health; then
  err "Health failed after deploy — rollback"
  rollback_frontend || exit 1
  exit 1
fi

step "Subsystem verification"
print_subsystems

step "Deploy complete"
END_TS="$(date +%s)"
DUR=$((END_TS - DEPLOY_START_TS))
log "Duration: $((DUR / 60))m $((DUR % 60))s | Build: ${BUILD_TIME}s"
log "Log file: $LOG_FILE"
ok "Site: https://papa-ai.ae (verify TLS / nginx as usual)"

exit 0
