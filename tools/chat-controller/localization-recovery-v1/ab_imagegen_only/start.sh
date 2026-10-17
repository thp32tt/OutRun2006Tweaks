#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p /profile /state /output /logs
if [[ -z "${VNC_PASSWORD:-}" ]]; then echo 'VNC_PASSWORD missing' >&2;exit 2;fi
x11vnc -storepasswd "$VNC_PASSWORD" /profile/.vncpasswd >/dev/null
Xvfb :99 -screen 0 1440x1000x24 -nolisten tcp > /logs/xvfb.log 2>&1 &
sleep 1
openbox > /logs/openbox.log 2>&1 &
x11vnc -display :99 -forever -shared -rfbauth /profile/.vncpasswd -rfbport 5900 -localhost -quiet > /logs/vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 127.0.0.1:5900 > /logs/novnc.log 2>&1 &
exec python -u /app/runner.py