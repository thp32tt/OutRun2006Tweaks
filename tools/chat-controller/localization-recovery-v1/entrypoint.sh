#!/usr/bin/env bash
set -euo pipefail

# Fail closed BEFORE Chrome/VNC or any saved browser automation can start.
# Fail closed unless the controlled native-crop -> A/B ImageGen -> C1 QA policy is valid.
python /opt/outrun/app/v2_automation_policy.py \
  --policy /opt/outrun/v2_docker_policy.json \
  --evidence-root /data/imagegen/korean_v2/stage_evidence


mkdir -p /data/browser-profile /data/state /logs /tmp/.X11-unix

# Repair read permissions left by older root-run C workers. These JSON files
# contain localization/OCR metadata only; no browser credentials or secrets.
C_OCR_REPORT="/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/hd108_ocr"
if [[ -d "$C_OCR_REPORT" ]]; then
  find "$C_OCR_REPORT" -type d -exec chmod 0755 {} + 2>/dev/null || true
  find "$C_OCR_REPORT" -type f -name '*.json' -exec chmod 0644 {} + 2>/dev/null || true
fi

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

start_crop_worker() {
  echo "$(date -Is) starting native English crop worker in shared controller container" >>/logs/c-english-crop.log
  python -u /opt/outrun/c_english_crop/loop.py \
    --interval-seconds "${OUTRUN_CROP_INTERVAL_SECONDS:-60}" \
    --max-per-cycle "${OUTRUN_CROP_MAX_PER_CYCLE:-10}" \
    >>/logs/c-english-crop.log 2>&1 &
}

if [[ "${OUTRUN_CROP_ENABLED:-true}" == "true" ]]; then
  start_crop_worker
  (
    CROP_HEARTBEAT="/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/crop_worker_heartbeat.json"
    CROP_STALL_SECONDS="${OUTRUN_CROP_STALL_SECONDS:-600}"
    while sleep 20; do
      restart_reason=""
      if ! pgrep -f "python -u /opt/outrun/c_english_crop/loop.py" >/dev/null 2>&1; then
        restart_reason="missing"
      elif [[ -f "$CROP_HEARTBEAT" ]]; then
        now_epoch="$(date +%s)"
        hb_epoch="$(stat -c %Y "$CROP_HEARTBEAT" 2>/dev/null || echo 0)"
        if (( now_epoch - hb_epoch > CROP_STALL_SECONDS )); then
          restart_reason="heartbeat_stale"
        fi
      fi
      if [[ -n "$restart_reason" ]]; then
        echo "$(date -Is) C crop worker $restart_reason; restarting" >>/logs/c-english-crop.log
        pkill -f "python -u /opt/outrun/c_english_crop/loop.py" >/dev/null 2>&1 || true
        sleep 2
        start_crop_worker
      fi
    done
  ) &
fi

# Legacy GPT OCR response watchdog remains disabled in the direct_visual GitOps profile.
if [[ "${OUTRUN_GPT_CHAT_OCR_ENABLED:-true}" == "true" ]]; then
  (
    while sleep "${OUTRUN_GPT_OCR_WATCHDOG_SECONDS:-60}"; do
      python -c 'from app.gpt_vision_chat_ocr import recover_stale_active; import json; print(json.dumps(recover_stale_active(), ensure_ascii=False))'         >>/logs/gpt-ocr-watchdog.log 2>&1 || true
    done
  ) &
fi

if [[ "${OUTRUN_ROI_BRIDGE_ENABLED:-true}" == "true" ]]; then
  echo "$(date -Is) verifying SHA-pinned direct visual ROI -> ImageGen queue sync" >>/logs/roi-bridge.log
  # Complete one fail-closed sync before AUTO_SEND controller startup. This
  # prevents a deployment exactly on a schedule minute from consuming stale Q104 state.
  # A bounded initial sync fails closed if the source/translation gate fails.
  timeout --signal=TERM --kill-after=10s 180s \
    python -u /opt/outrun/app/crop_to_imagegen_queue.py --once >>/logs/roi-bridge.log 2>&1
  echo "$(date -Is) starting supervised non-OCR bridge reconciliation" >>/logs/roi-bridge.log
  # A one-shot reconciliation restarts at every interval even if the prior
  # process exited; it cannot silently die and starve A/B of newly verified ROIs.
  # The last structured result is also visible in the existing shared N100 mount.
  (
    while true; do
      status_file=/data/imagegen/text_roi_batches/roi_bridge_last_result.json
      tmp_file=/data/imagegen/text_roi_batches/.roi_bridge_last_result.$.tmp
      if result="$(timeout --signal=TERM --kill-after=10s 180s \
          python -u /opt/outrun/app/crop_to_imagegen_queue.py --once 2>&1)"; then
        printf '%s %s\n' "$(date -Is)" "$result" >>/logs/roi-bridge.log
        printf '%s\n' "$result" > "$tmp_file"
      else
        code=$?
        echo "$(date -Is) ROI bridge failed/timeout (exit=$code), retrying" >>/logs/roi-bridge.log
        printf '{"status":"ROI_BRIDGE_RETRY","exit_code":%s}\n' "$code" > "$tmp_file"
      fi
      mv -f "$tmp_file" "$status_file"
      sleep "${OUTRUN_ROI_BRIDGE_INTERVAL_SECONDS:-60}"
    done
  ) &
fi

# Bound offline Korean fallback work to one source per loop by default.
# All generated DDS remain TEST_ONLY under the shared N100 image workspace.
# Portainer rebuild and redeploy are intentionally left to the user.
if [[ "${OUTRUN_OFFLINE_FALLBACK_ENABLED:-false}" == "true" ]]; then
  (
    while true; do
      echo "$(date -Is) starting bounded offline Korean fallback cycle" >>/logs/offline-korean.log
      if ! nice -n 15 timeout --signal=TERM --kill-after=15s 900s \
        python -u /opt/outrun/app/offline_korean_batch.py --execute \
          --max-sources "${OUTRUN_OFFLINE_FALLBACK_MAX_SOURCES_PER_CYCLE:-1}" \
          --mips "${OUTRUN_OFFLINE_FALLBACK_MIPS:-1}" \
          >>/logs/offline-korean.log 2>&1; then
        echo "$(date -Is) offline Korean fallback cycle held/failed; retry later" >>/logs/offline-korean.log
      fi
      sleep "${OUTRUN_OFFLINE_FALLBACK_INTERVAL_SECONDS:-300}"
    done
  ) &
fi

exec python -m app.controller