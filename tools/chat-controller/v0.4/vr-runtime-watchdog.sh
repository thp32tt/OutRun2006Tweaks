#!/usr/bin/env bash
# Independently supervise the controller event-loop heartbeat; /status runs in a
# separate thread and can keep responding while the queue is completely stuck.
set -euo pipefail

controller_pid="${1:?controller PID required}"
status_file="${VR_RUNTIME_WATCHDOG_FILE:-/data/state/runtime_status.json}"
started_marker="${VR_RUNTIME_WATCHDOG_MARKER:-/tmp/controller-started}"
log_file="${VR_RUNTIME_WATCHDOG_LOG:-/logs/runtime-watchdog.log}"
check_seconds="${VR_RUNTIME_WATCHDOG_CHECK_SECONDS:-30}"
stale_seconds="${VR_RUNTIME_WATCHDOG_STALE_SECONDS:-720}"
grace_seconds="${VR_RUNTIME_WATCHDOG_STARTUP_GRACE_SECONDS:-300}"

for value in "$controller_pid" "$check_seconds" "$stale_seconds" "$grace_seconds"; do
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    echo "Invalid VR runtime watchdog numeric setting" >&2
    exit 2
  fi
done
if (( check_seconds < 1 || stale_seconds < 2 || grace_seconds < 1 )); then
  echo "VR runtime watchdog intervals must be positive" >&2
  exit 2
fi

started_at=$(date +%s)
while sleep "$check_seconds"; do
  kill -0 "$controller_pid" 2>/dev/null || exit 0
  [[ -f "$started_marker" ]] || continue
  now=$(date +%s)
  (( now - started_at >= grace_seconds )) || continue

  # write_runtime() refreshes this file every 15 seconds from scheduler_loop.
  # /status is a different thread and does NOT refresh it.
  if [[ -f "$status_file" ]]; then
    last_update=$(stat -c '%Y' "$status_file" 2>/dev/null || printf 0)
  else
    last_update="$started_at"
  fi
  if (( now - last_update >= stale_seconds )); then
    mkdir -p "$(dirname "$log_file")"
    printf '%s no runtime heartbeat for %ds (PID=%d); terminating for Docker unless-stopped recovery\n' \
      "$(date -Is)" "$((now-last_update))" "$controller_pid" >> "$log_file"
    kill -TERM "$controller_pid" 2>/dev/null || true
    exit 0
  fi
done
