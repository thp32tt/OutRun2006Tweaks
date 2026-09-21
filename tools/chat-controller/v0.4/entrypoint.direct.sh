#!/usr/bin/env bash
set -euo pipefail

mkdir -p /data/browser-profile /data/state /logs /tmp/.X11-unix

VNC_PASSWORD="${VNC_PASSWORD:-change-me}"
PASSFILE=/data/.vncpasswd
x11vnc -storepasswd "$VNC_PASSWORD" "$PASSFILE" >/dev/null

rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1440x900x24 -ac +extension GLX +render -noreset >/logs/xvfb.log 2>&1 &
openbox >/logs/openbox.log 2>&1 &
x11vnc -display :99 -forever -shared -rfbauth "$PASSFILE" -rfbport 5900 -o /logs/x11vnc.log &
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/logs/novnc.log 2>&1 &

google-chrome --no-sandbox --disable-dev-shm-usage   --remote-debugging-address=127.0.0.1   --remote-debugging-port=9222   --user-data-dir=/data/browser-profile   --no-first-run --no-default-browser-check   https://chatgpt.com/ >/logs/chrome.log 2>&1 &

for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

exec python -m app.controller
