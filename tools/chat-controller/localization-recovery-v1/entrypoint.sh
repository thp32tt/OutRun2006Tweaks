#!/usr/bin/env bash
set -euo pipefail

mkdir -p /data/browser-profile /data/state /logs /tmp/.X11-unix

# Only clean after the previous container's Chrome is gone.
# Do not delete Cookies, Local Storage, IndexedDB or the saved registry.
if [[ "${CHROME_RECYCLE_ENABLED:-false}" == "true" ]]; then
  bash /opt/outrun/chrome-cache-clean.sh >>/logs/chrome-recycle.log 2>&1 || \
    echo "$(date -Is) cache cleaning failed; auth/profile kept" >>/logs/chrome-recycle.log
fi

VNC_PASSWORD="${VNC_PASSWORD:-change-me}"
PASSFILE=/data/.vncpasswd
x11vnc -storepasswd "$VNC_PASSWORD" "$PASSFILE" >/dev/null

rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1440x900x24 -ac +extension GLX +render -noreset >/logs/xvfb.log 2>&1 &
openbox >/logs/openbox.log 2>&1 &
start_vnc() {
  x11vnc -display :99 -forever -shared -rfbauth "$PASSFILE" -rfbport 5900 -o /logs/x11vnc.log &
}
start_vnc
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/logs/novnc.log 2>&1 &

start_chrome() {
  # Prevent profile corruption if an old Chrome process still holds the lock.
  for _chrome_stop_wait in 1 2 3 4 5; do
    if ! pgrep -x chrome >/dev/null 2>&1; then break; fi
    sleep 2
  done
  if pgrep -x chrome >/dev/null 2>&1; then
    echo "$(date -Is) Chrome still alive; refuse concurrent profile reuse" >>/logs/chrome-recycle.log
    return 0
  fi
  rm -f /data/browser-profile/SingletonLock \
        /data/browser-profile/SingletonCookie \
        /data/browser-profile/SingletonSocket
  # /dev/shm is sized to 1 GiB by compose, rather than using /tmp fallback.
  google-chrome --no-sandbox --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir=/data/browser-profile --no-first-run --no-default-browser-check https://chatgpt.com/ >>/logs/chrome.log 2>&1 &
}

start_chrome

# Keep UI dependencies alive even when x11vnc/Chrome exits while the controller remains healthy.
(
  while sleep 10; do
    if ! pgrep -x x11vnc >/dev/null 2>&1; then
      echo "$(date -Is) x11vnc missing; restarting" >>/logs/ui-watchdog.log
      start_vnc
    fi
    if ! curl -fsS http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
      echo "$(date -Is) Chrome DevTools unavailable; restarting Chrome" >>/logs/ui-watchdog.log
      pkill -x chrome >/dev/null 2>&1 || true
      sleep 2
      start_chrome
    fi
    if ! pgrep -f "websockify.*6080.*5900" >/dev/null 2>&1; then
      echo "$(date -Is) websockify missing; restarting" >>/logs/ui-watchdog.log
      websockify --web=/usr/share/novnc/ 6080 localhost:5900 >>/logs/novnc.log 2>&1 &
    fi
  done
) &

for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Refuse to start a controller that cannot attach to Chrome.
while ! curl -fsS http://127.0.0.1:9222/json/version >/dev/null 2>&1; do
  echo "$(date -Is) Chrome CDP absent; retrying" >>/logs/ui-watchdog.log
  pkill -x chrome >/dev/null 2>&1 || true
  sleep 3
  start_chrome
  sleep 7
done

exec python -m app.controller
