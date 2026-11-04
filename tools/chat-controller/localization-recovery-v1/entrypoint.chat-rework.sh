#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${OUTRUN_REWORK_VNC_PASSWORD:-}" ]]; then
  echo "HOLD: Set OUTRUN_REWORK_VNC_PASSWORD in Portainer before enabling chat browser." >&2
  exit 2
fi
umask 077
mkdir -p /data/hd-rework /data/browser-rework-profile /tmp/.X11-unix /logs
x11vnc -storepasswd "${OUTRUN_REWORK_VNC_PASSWORD}" /data/hd-rework/.vncpasswd >/dev/null 2>&1
Xvfb :99 -screen 0 1440x900x24 -ac -noreset >/logs/hd-rework-xvfb.log 2>&1 &
openbox >/logs/hd-rework-openbox.log 2>&1 &
x11vnc -display :99 -forever -shared -rfbauth /data/hd-rework/.vncpasswd \
  -rfbport 5900 >/logs/hd-rework-x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 127.0.0.1:5900 \
  >/logs/hd-rework-novnc.log 2>&1 &
exec python -u /opt/outrun/github_chat_rework_controller.py
