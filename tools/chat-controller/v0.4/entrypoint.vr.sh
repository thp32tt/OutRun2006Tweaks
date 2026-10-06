#!/usr/bin/env bash
set -euo pipefail

PROFILE_DIR=/data/browser-profile
mkdir -p "$PROFILE_DIR" /data/state /logs /tmp/.X11-unix
rm -f /tmp/controller-started

PROFILE_CACHE_PRUNE_ON_START="${PROFILE_CACHE_PRUNE_ON_START:-true}"
MAIN_PID=$$

prune_browser_cache() {
  if [[ "$PROFILE_CACHE_PRUNE_ON_START" != "true" ]]; then
    return
  fi
  # Preserve authentication/session stores. Remove only disposable Chrome caches
  # and stale process locks while Chrome is stopped.
  rm -rf     "$PROFILE_DIR/Default/Cache"     "$PROFILE_DIR/Default/Code Cache"     "$PROFILE_DIR/Default/GPUCache"     "$PROFILE_DIR/Default/DawnCache"     "$PROFILE_DIR/Default/Service Worker/CacheStorage"     "$PROFILE_DIR/GPUCache"     "$PROFILE_DIR/ShaderCache"     "$PROFILE_DIR/GrShaderCache"     "$PROFILE_DIR/DawnCache"     "$PROFILE_DIR/Crashpad/pending"     "$PROFILE_DIR/Crashpad/completed" 2>/dev/null || true
  rm -rf /tmp/.org.chromium.Chromium.* 2>/dev/null || true
  echo "$(date -Is) pruned disposable Chrome cache; persistent profile preserved" >>/logs/browser-recovery.log
}

clear_singleton_locks() {
  rm -f "$PROFILE_DIR/SingletonLock"         "$PROFILE_DIR/SingletonCookie"         "$PROFILE_DIR/SingletonSocket"
}

clear_singleton_locks
prune_browser_cache

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
  clear_singleton_locks
  prune_browser_cache
  google-chrome     --no-sandbox     --disable-dev-shm-usage     --remote-debugging-address=127.0.0.1     --remote-debugging-port=9222     --user-data-dir="$PROFILE_DIR"     --no-first-run     --no-default-browser-check     https://chatgpt.com/ >>/logs/chrome.log 2>&1 &
}

start_chrome

# UI/CDP watchdog. Before the controller starts, repair Chrome in place.
# After Playwright is attached, a CDP loss recycles the whole container so
# Chrome + Playwright + controller restart as one consistent unit.
(
  while sleep 10; do
    if ! pgrep -x x11vnc >/dev/null 2>&1; then
      echo "$(date -Is) x11vnc missing; restarting" >>/logs/ui-watchdog.log
      start_vnc
    fi

    if ! curl -fsS http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
      if [[ -f /tmp/controller-started ]]; then
        echo "$(date -Is) Chrome DevTools lost after controller attach; recycling container" >>/logs/browser-recovery.log
        rm -f /tmp/controller-started
        kill -TERM "$MAIN_PID" >/dev/null 2>&1 || true
        exit 0
      fi
      echo "$(date -Is) Chrome DevTools unavailable during startup; restarting Chrome" >>/logs/ui-watchdog.log
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

while ! curl -fsS http://127.0.0.1:9222/json/version >/dev/null 2>&1; do
  echo "$(date -Is) Chrome DevTools still unavailable before controller start; retrying" >>/logs/controller-startup.log
  pkill -x chrome >/dev/null 2>&1 || true
  sleep 2
  start_chrome
  sleep 8
done

echo "$(date -Is) starting VR controller" >>/logs/controller-startup.log
touch /tmp/controller-started
exec python -m app.controller
