# Localization Controller v2

## Production deployment entrypoint

Use only this controller for Korean localization production:

- Repository: `thp32tt/OutRun2006Tweaks`
- Branch: `chat-controller-downloads`
- Compose:
  `tools/chat-controller/v0.4-localization-v2/docker-compose.yml`

Do not deploy the older controller folders directly:

- `tools/chat-controller/v0.4` = legacy/reference
- `tools/chat-controller/localization` = previous localization fork/reference
- `tools/chat-controller/v0.5` = development/reference unless explicitly promoted

## Runtime

Portainer (Docker Standalone, amd64): configure:

- `LOCALIZATION_PROJECT_URL`
- `GITHUB_TOKEN`
- `VNC_PASSWORD`

Start with `AUTO_SEND=false`, verify ChatGPT project and GitHub connection, then enable `AUTO_SEND=true` and redeploy.

## Localization worker model

The production controller uses independent parallel lanes:

```text
Producer A  ─────┐                      ┌── QA Validator C1
                 ├── Artifact Queue ─────┤
Producer B  ─────┘                      └── QA Validator C2
```

### Producer lanes

- A and B continuously produce DDS localization candidates.
- A and B are independent production workers.
- A/B production must not stop because unrelated assets are waiting for QA.
- Every candidate must include the required artifact evidence before entering QA.

### QA lanes

- C1 and C2 independently consume *different* completed A/B artifacts from one durable QA queue.
- Candidate path/SHA cannot be assigned twice, including across restarts.
- Both use the strict QA rules in `localization_C.md`, with distinct lane names and commit markers.
- PASS/REWORK decisions apply to the affected asset only; producer A/B does not wait for an unrelated QA.
- The previous C lane's URL, runs and active task are migrated to C1; C2 starts empty.

## State and source rules

- GitHub remains the SSOT for code, state definitions, and tracked changes.
- N100 remote execution is supported for controller operation, Docker management, and Portainer deployment.
- Approved Google Drive canonical HD source transport may be used for original DDS acquisition.
- Drive DDS sources must preserve checksum, dimensions, format, alpha, mip requirements, and localization quality gates.
- Existing localization artifacts and VR deployment remain separate.

## Slot model

Localization execution uses four logical workers:

```text
slot-1 = Producer A
slot-2 = Producer B
slot-3 = QA C1
slot-4 = QA C2
```

Restarting the controller must preserve this role separation.

## Queue rules

- Production queue continues while QA is processing other assets.
- Blocking is asset-scoped, not global.
- Rework only returns the affected asset to production.
- Completed assets are not reprocessed unless explicitly reopened by QA.

## Build

```sh
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml config
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml build
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml up -d
```

The image builds from `v0.4/src` and uses A/B/C localization prompts. VR controller deployment is independent. Do not delete existing volumes. Runtime game validation remains `UNTESTED` until performed.

## Chrome tab recovery (2026-10-10)

The production image builds the shared `v0.4/src/controller.py.part*`
controller (NOT the older `localization/src` fork). This release has four **worker** tabs by policy: producer A, producer B,
independent QA C1, independent QA C2. Any older three-worker statement is
superseded by the four-lane implementation.

The A/B/C1/C2 tab-health task runs independently of slow queue operations,
defaulting to one pass every 30 seconds. It detects:
- a missing/closed tab;
- Playwright renderer `crash` events;
- Chromium "Aw, Snap!", `chrome-error://`, and related error pages;
- a renderer that fails the probe three consecutive times;
- a failed prior recovery navigation.

Chromium error pages are confirmed twice before replacement. The watcher
only closes and reopens the affected tab and navigates to the **persisted
ChatGPT conversation URL** when it belongs to the configured project. It
never sends or retries prompts; it does not change production IDs, queue
phases, attempts, or saved progress. Already-running healthy tabs are not
recycled. Failed page replacement is logged and retried after cooldown.

Configurable environment values in `docker-compose.yml`:
`TAB_HEALTH_CHECK_SECONDS=30`, `TAB_HEALTH_PROBE_TIMEOUT_SECONDS=6`,
`TAB_HEALTH_FAILURE_THRESHOLD=3`, `TAB_ERROR_FAILURE_THRESHOLD=2`,
`TAB_RECOVERY_COOLDOWN_SECONDS=60`.

Inspect `/logs/controller.log`, `/logs/chrome.log`,
`/logs/ui-watchdog.log`, `/logs/tab-recovery/` screenshots, and
`/data/state/runtime_status.json` for
`tab_recovery_count`, `tab_recovery_last_slot`,
`tab_recovery_last_reason`, `tab_recovery_error`.
For repeated failures, check Docker `OOMKilled` and container memory
usage against `mem_limit: 4g` and `shm_size: 1g` (cause unverified until live logs are read).

Run `python tests/test_localization_tab_recovery.py` to verify isolated
recovery before redeployment. Rebuild/redeploy the **v2** stack to apply
the code; preserve the named data and log volumes. The older standalone
`tools/chat-controller/localization/` image is not the v2 production
image and does not inherit this fix automatically.

## Four-worker rollout validation

Run `python tools/chat-controller/v0.4/tests/test_event_model_v2.py` and `python tests/test_localization_tab_recovery.py`, then check the exact new image after rebuilding the v2 stack. Status page should display slot names `A,B,C1,C2`, a non-destructive previous C-to-C1 migration, and `tab_count: 4`. The monitor retains separate C1/C2 counters and saved URLs. GitHub Actions passing does not imply Portainer is redeployed. Old standalone controller compose/source files are legacy; use this v2 production stack. Memory limits are a starting guardrail; use container logs/OOMKilled to tune them if failures continue.

## Scheduled Chrome cache reset without re-login

Production v2 (four-worker A/B/C1/C2 stack) enables:

- CHROME_RECYCLE_ENABLED=true
- CHROME_RECYCLE_INTERVAL_MINUTES=120 (from controller start)
- CHROME_RECYCLE_BUSY_GRACE_MINUTES=30
- CHROME_RECYCLE_BUSY_PROBE_SECONDS=8

At the interval, if no worker is generating a response, the controller
checkpoints /data/state/chat_registry.json and
/data/state/chrome_recycle.json, then exits with code 75.
Docker restart: unless-stopped starts a fresh Chrome/controller session
using the original named volumes. The four workers' saved conversation
URLs and exact asset/SHA work state are reattached. If any worker is
generating (or busy state cannot be confirmed), the restart is deferred
for up to 30 minutes. At the maximum delay, the current in-browser response
may be interrupted; no duplicate task send is performed.

Before Chrome starts, chrome-cache-clean.sh removes ONLY disposable
cache directories (Cache, Code Cache, GPUCache, ShaderCache, GrShaderCache,
DawnCache, Default/Media Cache and Default/Network/Cache). It NEVER deletes
Network/Cookies, Cookies, Login Data, Preferences, Local Storage,
IndexedDB, Session Storage, Sessions, Service Worker data, GitHub task
records, or the full browser-profile volume. The helper refuses symlinked
profile roots and never cleans a running Chrome process. Persistent files
are preserved; an expired remote login session can still require login.

Inspect /logs/chrome-recycle.log, /logs/controller.log and
/data/state/chrome_recycle.json, plus /status fields
chrome_recycle_status, chrome_recycle_last_at,
chrome_recycle_next_due_at, chrome_recycle_deferred_slots and
chrome_recycle_count. Scheduled restart is not a new TASK/attempt.

Regression:
- python tests/test_localization_chrome_recycle.py
- bash tools/chat-controller/v0.4/tests/test_chrome_cache_clean.sh

Rebuild/redeploy only the dedicated v2 stack from chat-controller-downloads;
keep both named volumes. GitHub CI success does not deploy Portainer.
