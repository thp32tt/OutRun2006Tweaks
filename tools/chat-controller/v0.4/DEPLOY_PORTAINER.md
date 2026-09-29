# OutRun Chat Controller v0.4 — Portainer deployment

## Architecture

N100 runs only the browser/controller containers. Project work must be performed directly against GitHub by ChatGPT.

- VR SSOT: `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`
- Korean localization SSOT: `thp32tt/OutRun2006Tweaks` / `korean-localization-clean`
- Do not use N100 local clones/worktrees as project workspaces.
- Each ChatGPT account must have working GitHub read/write access before AUTO_SEND is enabled.

## Portainer Git source

Repository:
`https://github.com/thp32tt/OutRun2006Tweaks.git`

Reference:
`refs/heads/chat-controller-downloads`

## VR stack

Stack name:
`outrun-chat-vr`

Compose path:
`tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`

Environment variables:

- `VR_PROJECT_URL=https://chatgpt.com/g/g-p-6ab9a64fc428819198c7f39765d764bf/project`
- `AUTO_SEND=false`
- `WATCHDOG_ENABLED=false`
- `VNC_PASSWORD=<your password>`

Access:

- noVNC: `http://<N100-IP>:6080`
- status: `http://<N100-IP>:8787`

Log in with the VR ChatGPT account and verify the configured project opens. The controller also pins `EXPECTED_PROJECT_ID=g-p-6ab9a64fc428819198c7f39765d764bf`; if `VR_PROJECT_URL` points at another project, `AUTO_SEND` is disabled.

## Localization stack

Stack name:
`outrun-chat-localization`

Compose path:
`tools/chat-controller/v0.4/docker-compose.portainer-localization.yml`

Environment variables:

- `LOCALIZATION_PROJECT_URL=<full ChatGPT localization project URL>`
- `AUTO_SEND=false`
- `WATCHDOG_ENABLED=false`
- `VNC_PASSWORD=<your password>`

Access:

- noVNC: `http://<N100-IP>:6081`
- status: `http://<N100-IP>:8788`

Log in with the localization ChatGPT account and verify the configured project opens.

## Before enabling automation

For each account:

1. Verify the correct ChatGPT account is logged in.
2. Verify the configured ChatGPT project opens from noVNC.
3. Verify GitHub read/write access is available to ChatGPT.
4. Run one manual task and confirm GitHub is used directly.
5. Confirm no N100 local clone/worktree is used for project changes.

Then change `AUTO_SEND=true` in that Portainer stack and redeploy.

`REQUIRE_PROJECT_URL=true` is built into both compose files. If the project URL is missing, AUTO_SEND is blocked even when requested.

## Isolation

VR volumes:
- `outrun_chat_vr_data`
- `outrun_chat_vr_logs`

Localization volumes:
- `outrun_chat_localization_data`
- `outrun_chat_localization_logs`

Never share `/data` between the two stacks. It contains the Chrome profile, login session, controller state, and VNC password file.

## Current resource limits

Each controller:

- memory hard limit: 3 GiB
- memory reservation: 1 GiB
- CPU limit: 1.5
- shared memory: 768 MiB

## Safety

If GitHub access is unavailable, the controller prompt instructs ChatGPT to report the failure. It must not fall back to the N100 local repository.


## Queue mode (v0.5 behavior in v0.4 deployment path)

Both existing Portainer compose paths now run the GitHub-gated queue engine.

### Conversion stack
The existing `docker-compose.portainer-vr.yml` path is retained for compatibility, but its controller mode is now `conversion`.

- lane A: DX11 -> `vr-dx11-native-r71`
- lane B: DXVK -> `vr-dxvk-r71-disasm`
- required workflow: `Backend Conversion Gate`
- only one modifying task is active at a time
- successful automatic validation advances immediately to the next independent lane
- runtime/HMD validation remains `UNTESTED` unless separately proven

### Localization stack
- lane A/B/C: production / exhaustive QA / final QA
- branch: `korean-localization-clean`
- required workflow: `Localization Automation Gate`
- automatic validation may advance while runtime validation remains `UNTESTED`

### Controller completion rule
A chat response is not completion. The controller requires:
1. target branch HEAD changed from the task base SHA;
2. result commit message contains `[AUTO:<TASK_ID>]`;
3. required GitHub Actions workflow exists for that exact result SHA;
4. workflow conclusion is `success`.

A missing workflow run remains validation-pending. A failed run triggers a repair turn in the same task chat. Maximum repair attempts: 3. After that, the task is recorded BLOCKED and the controller advances to another independent task.

### Watchdog
In queue mode the watchdog may recover Retry / Continue generating / browser-composer failures, but it does not select or send the next work item. Task ownership remains with the queue engine.

### Recommended environment
```
AUTO_SEND=true
WATCHDOG_ENABLED=true
QUEUE_MODE=true
PREFERRED_THINKING_LEVEL=High
STRICT_THINKING_LEVEL=true
GITHUB_POLL_SECONDS=60
MAX_TASK_ATTEMPTS=3
```

`STRICT_THINKING_LEVEL=true` is mandatory for automated sends. If High cannot be positively verified in the ChatGPT UI, the controller must block that send instead of falling back to another thinking level.

If Portainer does not auto-pull Git changes, use **Pull and redeploy** for each stack after this controller update.

## Localization parallel waves

When `LOCALIZATION_PARALLEL=true`, the localization controller uses a wave barrier:

1. Lane A starts on the odd-index asset_queue shard.
2. Lane B starts after `PARALLEL_LANE_STAGGER_SECONDS` (default 15s) on the even-index shard.
3. A and B run concurrently in separate project chats and may not modify shared resume/worklog/progress/asset_queue state.
4. Each lane is completed by locating its exact `[AUTO:<TASK_ID>]` commit in branch history and validating GitHub Actions for that exact SHA; branch HEAD may belong to the peer lane and is not used as the lane completion identity.
5. After both production lanes reach a durable terminal result, C starts as the synchronization barrier, performs cross-lane final QA, and reconciles shared state.
6. After C is terminal, the next A+B wave begins.

The existing single-active queue state is migrated on first startup: an in-flight A/B task becomes that lane of the first parallel wave, and the missing peer lane is dispatched without discarding the existing task.


### Localization liveness tuning

The localization stack now uses these controller-runtime values directly:

- queue loop: 15s
- missing-response/no-commit grace: 180s (previously 1800s)
- Actions discovery: 60s
- bound exact Actions run polling: 30s, uncached
- stale WAIT_ACTIONS rearm: 75s
- idle queue rearm: 90s
- next-task delay: 15s
- A/B lane stagger: 15s
- distinct A/B slot send gap: 15s
- scheduler heartbeat: 15s
- active-generation busy-stall protection: 30m
- explicit rate-limit backoff: 90/180/300/600s

On startup, persisted nonterminal queue records are reconciled. WAIT_ACTIONS poll guards are cleared so the next queue cycle checks the stored GitHub Actions run ID directly. A failed terminal run retries the same TASK_ID while retry budget remains, after refreshing the current target-branch HEAD.

When redeploying in Portainer, retain the existing localization /data volume so persisted W00018 state can be reconciled instead of discarded.
