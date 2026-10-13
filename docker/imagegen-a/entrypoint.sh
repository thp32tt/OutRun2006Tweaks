#!/usr/bin/env bash
set -euo pipefail
mkdir -p /data/browser-profile /data/results /logs /tmp/.X11-unix
: "${VNC_PASSWORD:?VNC_PASSWORD required}"
x11vnc -storepasswd "$VNC_PASSWORD" /data/.vncpasswd >/dev/null
Xvfb :99 -screen 0 1440x900x24 -ac +extension GLX +render -noreset >/logs/xvfb.log 2>&1 &
for i in $(seq 1 30); do xdpyinfo -display :99 >/dev/null 2>&1 && break; sleep 1; done
openbox >/logs/openbox.log 2>&1 &
x11vnc -display :99 -forever -shared -rfbauth /data/.vncpasswd -rfbport 5900 -o /logs/x11vnc.log &
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/logs/novnc.log 2>&1 &
# Fresh stack volume only: never share a running Chrome profile with the old stack.
rm -f /data/browser-profile/SingletonLock /data/browser-profile/SingletonCookie /data/browser-profile/SingletonSocket
google-chrome --no-sandbox --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir=/data/browser-profile --no-first-run --no-default-browser-check https://chatgpt.com/ >/logs/chrome.log 2>&1 &
for i in $(seq 1 60); do curl -fsS http://127.0.0.1:9222/json/version >/dev/null && break; sleep 1; done
exec python -m app.controller
