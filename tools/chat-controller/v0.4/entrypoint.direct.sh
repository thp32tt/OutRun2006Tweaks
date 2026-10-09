#!/usr/bin/env bash
set -euo pipefail

mkdir -p /data/browser-profile /data/state /logs /tmp/.X11-unix

# Chrome may leave ProcessSingleton files behind after a container is replaced or
# killed. They are safe to remove here because Chrome has not been started yet in
# this container. Stale locks otherwise make Chrome exit immediately and can
# cause an endless container restart loop.
rm -f /data/browser-profile/SingletonLock \
      /data/browser-profile/SingletonCookie \
      /data/browser-profile/SingletonSocket

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
  # Never remove singleton locks or cache while an old Chrome still owns
  # this profile; a concurrent launch would corrupt saved credentials.
  for _chrome_stop_wait in 1 2 3 4 5; do
    if ! pgrep -x chrome >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  if pgrep -x chrome >/dev/null 2>&1; then
    echo "$(date -Is) Chrome still running; postpone profile reuse" >>/logs/chrome-recycle.log
    return 0
  fi
  # Only localization v2 enables this feature. Chrome must be stopped before
  # cache deletion; credentials, profile storage and sessions are never removed.
  if [[ "${CONTROLLER_MODE:-}" == "localization" && "${CHROME_RECYCLE_ENABLED:-false}" == "true" ]]; then
    if ! pgrep -x chrome >/dev/null 2>&1; then
      if [[ -f /opt/outrun/chrome-cache-clean.sh ]]; then
        bash /opt/outrun/chrome-cache-clean.sh >>/logs/chrome-recycle.log 2>&1 || \
          echo "$(date -Is) cache cleanup failed; keeping profile intact" >>/logs/chrome-recycle.log
      fi
    else
      echo "$(date -Is) cache cleanup skipped: Chrome still running" >>/logs/chrome-recycle.log
    fi
  fi
  # A previous Chrome crash/replacement can leave ProcessSingleton files behind.
  # Remove them only immediately before starting a new Chrome process.
  rm -f /data/browser-profile/SingletonLock \
        /data/browser-profile/SingletonCookie \
        /data/browser-profile/SingletonSocket
  google-chrome --no-sandbox --disable-dev-shm-usage --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir=/data/browser-profile --no-first-run --no-default-browser-check https://chatgpt.com/ >>/logs/chrome.log 2>&1 &
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

# Do not start the controller into a guaranteed attach failure. Keep the UI
# container alive and retry Chrome until DevTools is really reachable.
while ! curl -fsS http://127.0.0.1:9222/json/version >/dev/null 2>&1; do
  echo "$(date -Is) Chrome DevTools still unavailable before controller start; retrying" >>/logs/controller-startup.log
  pkill -x chrome >/dev/null 2>&1 || true
  sleep 2
  start_chrome
  sleep 8
done

echo "$(date -Is) starting controller" >>/logs/controller-startup.log
exec python -m app.controller
