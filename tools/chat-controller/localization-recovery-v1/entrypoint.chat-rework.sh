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

# A missing/invalid GitHub token is a worker HOLD, not a reason to prevent
# VNC access for initial ChatGPT login and troubleshooting.
while true; do
  if ! kill -0 "$novnc_pid" 2>/dev/null || ! kill -0 "$vnc_pid" 2>/dev/null; then
    echo "HOLD_NOVNC_PROCESS_STOPPED: Review /logs/hd-rework-novnc.log." >&2
    exit 3
  fi
  if [[ -z "${OUTRUN_GITHUB_CONTENTS_TOKEN:-}" ]]; then
    echo "HOLD_GITHUB_CONTENTS_TOKEN_MISSING: VNC remains available; configure token in Portainer." >&2
    sleep 60 &
    wait "$!" || true
    continue
  fi
  echo "START_CHAT_REWORK_WORKER: GitHub QA queue; no DDS encoding on N100." >&2
  set +e
  python -u /opt/outrun/github_chat_rework_controller.py
  rc=$?
  set -e
  echo "HOLD_CHAT_REWORK_EXITED: exit_code=$rc; VNC remains running, retrying in 60 seconds." >&2
  sleep 60 &
  wait "$!" || true
done
