#!/usr/bin/env bash
set -euo pipefail

PROFILE_DIR=/data/browser-profile
mkdir -p "$PROFILE_DIR" /data/state /logs
VR_BROWSER_MODE="${VR_BROWSER_MODE:-headless}"
case "$VR_BROWSER_MODE" in
  headless|gui) ;;
  *) echo "Invalid VR_BROWSER_MODE: use headless or gui" >&2; exit 2 ;;
esac
export VR_BROWSER_MODE
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

# Use the same installed Chromium-based Google Chrome and the same user-data-dir
# in both modes. Do not migrate cookies to another browser or expose CDP remotely.
start_vnc() {
  x11vnc -display :99 -forever -shared -rfbauth "$PASSFILE" -rfbport 5900 -o /logs/x11vnc.log &
}
start_novnc() {
  websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/logs/novnc.log 2>&1 &
}
start_desktop() {
  [[ "$VR_BROWSER_MODE" == "gui" ]] || return 0
  mkdir -p /tmp/.X11-unix
  PASSFILE=/data/.vncpasswd
  x11vnc -storepasswd "${VNC_PASSWORD:-change-me}" "$PASSFILE" >/dev/null
  rm -f /tmp/.X99-lock
  Xvfb :99 -screen 0 1440x900x24 -ac +extension GLX +render -noreset >/logs/xvfb.log 2>&1 &
  openbox >/logs/openbox.log 2>&1 &
  start_vnc
  start_novnc
}

build_chrome_args() {
  CHROME_ARGS=(
    --no-sandbox --disable-dev-shm-usage
    --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222
    --user-data-dir="$PROFILE_DIR"
    --no-first-run --no-default-browser-check
  )
  if [[ "$VR_BROWSER_MODE" == "headless" ]]; then
    CHROME_ARGS+=(--headless=new --window-size=1280,800 --disable-extensions)
  fi
  # Do not open an extra ChatGPT home renderer. The controller owns navigation.
  CHROME_ARGS+=(about:blank)
}

start_chrome() {
  build_chrome_args
  google-chrome "${CHROME_ARGS[@]}" >>/logs/chrome.log 2>&1 &
  CHROME_PID=$!
}

cdp_ready() {
  curl -fsS --connect-timeout 2 --max-time 4 http://127.0.0.1:9222/json/version >/dev/null 2>&1
}

start_desktop
start_chrome
echo "$(date -Is) VR browser mode=$VR_BROWSER_MODE (persistent profile; single A slot)" >>/logs/browser-recovery.log

# No repeated startup Chrome launches: if the one browser cannot start, exit
# and let Docker restart the complete container. Never clear a live profile lock.
ready=false
for i in $(seq 1 60); do
  if cdp_ready; then
    ready=true
    break
  fi
  if ! kill -0 "$CHROME_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo "$(date -Is) Chrome CDP startup failed; recycle container" >>/logs/browser-recovery.log
  exit 1
fi

# After attach, restart the entire container only after repeated CDP failures.
# GUI helpers are monitored exclusively in GUI mode, never started in headless.
(
  misses=0
  while sleep 15; do
    if cdp_ready; then
      misses=0
    else
      misses=$((misses+1))
      if (( misses >= 3 )); then
        echo "$(date -Is) Chrome CDP failed three probes; recycling container" >>/logs/browser-recovery.log
        kill -TERM "$MAIN_PID" >/dev/null 2>&1 || true
        exit 0
      fi
    fi
    if [[ "$VR_BROWSER_MODE" == "gui" ]]; then
      if ! pgrep -x x11vnc >/dev/null 2>&1; then
        start_vnc
      fi
      if ! pgrep -f "websockify.*6080.*5900" >/dev/null 2>&1; then
        start_novnc
      fi
    fi
  done
) &

echo "$(date -Is) starting VR controller" >>/logs/controller-startup.log
touch /tmp/controller-started
# A separate process detects a frozen scheduler even when the threaded /status
# endpoint and Docker healthcheck still report HTTP 200.
/opt/outrun/vr-runtime-watchdog.sh "$MAIN_PID" &
exec python -m app.controller
