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
Producer A  ─────┐
                 ├── Artifact Queue ─── QA Validator C
Producer B  ─────┘
```

### Producer lanes

- A and B continuously produce DDS localization candidates.
- A and B are independent production workers.
- A/B production must not stop because unrelated assets are waiting for QA.
- Every candidate must include the required artifact evidence before entering QA.

### QA lane

- C continuously consumes completed A/B artifacts.
- C validates producer output using the required QA rules.
- C PASS/REWORK decisions apply to the affected asset only.
- A QA failure must not block unrelated production assets.

## State and source rules

- GitHub remains the SSOT for code, state definitions, and tracked changes.
- N100 remote execution is supported for controller operation, Docker management, and Portainer deployment.
- Approved Google Drive canonical HD source transport may be used for original DDS acquisition.
- Drive DDS sources must preserve checksum, dimensions, format, alpha, mip requirements, and localization quality gates.
- Existing localization artifacts and VR deployment remain separate.

## Slot model

Localization execution uses three logical workers:

```text
slot-1 = Producer A
slot-2 = Producer B
slot-3 = QA C
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

The production image builds the shared \`v0.4/src/controller.py.part*\`
controller (NOT the older \`localization/src\` fork). This release has three
**worker** tabs by design: producer A, producer B, QA C. A fourth tab is
not an independent worker and is not created automatically.

The A/B/C tab-health task runs independently of slow queue operations,
defaulting to one pass every 30 seconds. It detects:
- a missing/closed tab;
- Playwright renderer \`crash\` events;
- Chromium "Aw, Snap!", \`chrome-error://\`, and related error pages;
- a renderer that fails the probe three consecutive times;
- a failed prior recovery navigation.

Chromium error pages are confirmed twice before replacement. The watcher
only closes and reopens the affected tab and navigates to the **persisted
ChatGPT conversation URL** when it belongs to the configured project. It
never sends or retries prompts; it does not change production IDs, queue
phases, attempts, or saved progress. Already-running healthy tabs are not
recycled. Failed page replacement is logged and retried after cooldown.

Configurable environment values in \`docker-compose.yml\`:
\`TAB_HEALTH_CHECK_SECONDS=30\`, \`TAB_HEALTH_PROBE_TIMEOUT_SECONDS=6\`,
\`TAB_HEALTH_FAILURE_THRESHOLD=3\`, \`TAB_ERROR_FAILURE_THRESHOLD=2\`,
\`TAB_RECOVERY_COOLDOWN_SECONDS=60\`.

Inspect \`/logs/controller.log\`, \`/logs/chrome.log\`,
\`/logs/ui-watchdog.log\`, \`/logs/tab-recovery/\` screenshots, and
\`/data/state/runtime_status.json\` for
\`tab_recovery_count\`, \`tab_recovery_last_slot\`,
\`tab_recovery_last_reason\`, \`tab_recovery_error\`.
For repeated failures, check Docker \`OOMKilled\` and container memory
usage against \`mem_limit: 3g\` (cause unverified until live logs are read).

Run \`python tests/test_localization_tab_recovery.py\` to verify isolated
recovery before redeployment. Rebuild/redeploy the **v2** stack to apply
the code; preserve the named data and log volumes. The older standalone
\`tools/chat-controller/localization/\` image is not the v2 production
image and does not inherit this fix automatically.
