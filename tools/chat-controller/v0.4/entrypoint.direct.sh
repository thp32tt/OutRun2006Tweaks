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

exec python -m app.controller
