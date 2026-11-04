#!/usr/bin/env bash
# Keep authenticated VNC available for diagnostics even if the GitHub bridge
# lacks a token or its browser session/API temporarily fails.
set -euo pipefail

if [[ -z "${OUTRUN_REWORK_VNC_PASSWORD:-}" ]]; then
  echo "HOLD_VNC_PASSWORD_MISSING: Set OUTRUN_REWORK_VNC_PASSWORD in Portainer. Refusing passwordless VNC." >&2
  exit 2
fi

umask 077
mkdir -p /data/hd-rework /data/browser-rework-profile /tmp/.X11-unix /logs
if ! x11vnc -storepasswd "${OUTRUN_REWORK_VNC_PASSWORD}" /data/hd-rework/.vncpasswd >/dev/null 2>&1; then
  echo "HOLD_VNC_PASSWORD_FILE_FAILED: Check mounted /data permissions." >&2
  exit 2
fi

Xvfb :99 -screen 0 1440x900x24 -ac -noreset >/logs/hd-rework-xvfb.log 2>&1 &
xvfb_pid=$!
for _ in $(seq 1 40); do
  if [[ -S /tmp/.X11-unix/X99 ]]; then break; fi
  if ! kill -0 "$xvfb_pid" 2>/dev/null; then
    echo "HOLD_XVFB_EXITED: Review /logs/hd-rework-xvfb.log." >&2
    exit 3
  fi
  sleep 0.25
done
if [[ ! -S /tmp/.X11-unix/X99 ]]; then
  echo "HOLD_XVFB_SOCKET_MISSING: Review /logs/hd-rework-xvfb.log." >&2
  exit 3
fi

openbox >/logs/hd-rework-openbox.log 2>&1 &
openbox_pid=$!
x11vnc -display :99 -forever -shared -rfbauth /data/hd-rework/.vncpasswd \
  -rfbport 5900 >/logs/hd-rework-x11vnc.log 2>&1 &
vnc_pid=$!
websockify --web=/usr/share/novnc 6080 127.0.0.1:5900 \
  >/logs/hd-rework-novnc.log 2>&1 &
novnc_pid=$!

shutdown() {
  trap - INT TERM
  if [[ -n "${chrome_pid:-}" ]]; then kill "$chrome_pid" 2>/dev/null || true; fi
  kill "$novnc_pid" "$vnc_pid" "$openbox_pid" "$xvfb_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap 'shutdown; exit 0' INT TERM

sleep 1
if ! kill -0 "$novnc_pid" 2>/dev/null || ! kill -0 "$vnc_pid" 2>/dev/null; then
  echo "HOLD_NOVNC_START_FAILED: Review /logs/hd-rework-x11vnc.log and hd-rework-novnc.log." >&2
  exit 3
fi
echo "NOVNC_LISTENER_STARTED: container port 6080, host port configured by Compose (default 6084)." >&2

# Acquire an exclusive filesystem lock before touching the shared persistent
# Chromium profile. flock is kernel-managed and automatically released on death.
# Never delete cookies, login data, bookmarks, settings, or browser history.
profile_dir=/data/hd-rework/browser-rework-profile
mkdir -p "$profile_dir"
exec 9>"$profile_dir/.outrun-profile-owner.lock"
if ! flock -n 9; then
  echo "HOLD_BROWSER_PROFILE_IN_USE: another instance owns this shared profile; no lockfiles will be deleted." >&2
  exit 5
fi

recover_stale_chrome_singletons() {
  local name lock cleaned=0
  # Do not modify locks if Chrome is already alive for this profile.
  if ps -eo args | grep -F -- "--user-data-dir=$profile_dir" | grep -F '/ms-playwright/' | grep -v '[g]rep' >/dev/null 2>&1; then
    echo "HOLD_BROWSER_PROFILE_HAS_LIVE_CHROMIUM: refusing to remove Singleton files." >&2
    return 1
  fi
  for name in SingletonLock SingletonSocket SingletonCookie; do
    lock="$profile_dir/$name"
    # Singleton files are symlinks; never remove a directory or regular data.
    if [[ -L "$lock" ]]; then
      rm -- "$lock"
      cleaned=$((cleaned+1))
    fi
  done
  if [[ -f "$profile_dir/DevToolsActivePort" && ! -L "$profile_dir/DevToolsActivePort" ]]; then
    rm -- "$profile_dir/DevToolsActivePort"
  fi
  echo "BROWSER_PROFILE_STALE_SINGLETON_RECOVERY: removed $cleaned lock symlinks under exclusive profile flock; user data untouched." >&2
}

# Start a genuine visible Chromium window independently of the task queue.
# The Python A/B/C1 worker connects to THIS SAME browser over local-only CDP,
# so manually authenticated ChatGPT sessions remain in the correct profile.
launch_visible_chrome() {
  local chrome
  if ! recover_stale_chrome_singletons; then
    return 1
  fi
  chrome="$(python - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    print(pw.chromium.executable_path)
PY
)"
  if [[ ! -x "$chrome" ]]; then
    echo "HOLD_CHROMIUM_EXECUTABLE_MISSING: $chrome" >&2
    return 1
  fi
  "$chrome" --no-sandbox --disable-gpu \
    --no-first-run --no-default-browser-check --password-store=basic \
    --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 \
    --user-data-dir=/data/hd-rework/browser-rework-profile \
    --new-window "https://chatgpt.com/" \
    >/logs/hd-rework-chromium.log 2>&1 &
  chrome_pid=$!
  for _ in $(seq 1 80); do
    if ! kill -0 "$chrome_pid" 2>/dev/null; then
      echo "HOLD_CHROMIUM_EXITED: Review /logs/hd-rework-chromium.log." >&2
      return 1
    fi
    if python - <<'PY' >/dev/null 2>&1
import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:9222/json/version",timeout=1) as r:
    v=json.load(r)
assert "webSocketDebuggerUrl" in v
PY
    then
      echo "CHROMIUM_LOGIN_WINDOW_READY: DISPLAY=:99; CDP loopback 127.0.0.1:9222; no host CDP port." >&2
      return 0
    fi
    sleep 0.5
  done
  echo "HOLD_CHROMIUM_CDP_TIMEOUT: Review /logs/hd-rework-chromium.log." >&2
  return 1
}

until launch_visible_chrome; do
  echo "HOLD_VISIBLE_BROWSER_START_FAILED: noVNC remains running; retry in 30 seconds. Review /logs/hd-rework-chromium.log." >&2
  if [[ -n "${chrome_pid:-}" ]]; then
    kill "$chrome_pid" 2>/dev/null || true
    wait "$chrome_pid" 2>/dev/null || true
  fi
  sleep 30 &
  wait "$!" || true
done


# A missing/invalid GitHub token is a worker HOLD, not a reason to prevent
# VNC access for initial ChatGPT login and troubleshooting.
while true; do
  if ! kill -0 "$novnc_pid" 2>/dev/null || ! kill -0 "$vnc_pid" 2>/dev/null; then
    echo "HOLD_NOVNC_PROCESS_STOPPED: Review /logs/hd-rework-novnc.log." >&2
    exit 3
  fi
  if [[ -z "${OUTRUN_GITHUB_CONTENTS_TOKEN:-}" ]]; then
    echo "HOLD_GITHUB_CONTENTS_TOKEN_MISSING: opening ChatGPT login window anyway; queue stays paused." >&2
  fi
  echo "START_CHAT_REWORK_WORKER: show ChatGPT login window before queue, no DDS encoding on N100." >&2
  set +e
  python -u /opt/outrun/github_chat_rework_controller.py
  rc=$?
  set -e
  echo "HOLD_CHAT_REWORK_EXITED: exit_code=$rc; VNC remains running, retrying in 60 seconds." >&2
  sleep 60 &
  wait "$!" || true
done
