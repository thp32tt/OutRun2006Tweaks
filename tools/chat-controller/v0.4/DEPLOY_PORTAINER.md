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

VR conversion controller:

- memory hard limit: 5 GiB
- memory reservation: 2 GiB
- CPU limit: 1.5
- shared memory: 768 MiB
- fatal Playwright/CDP transport loss exits the controller so `restart: unless-stopped` can recover the container

Localization controller:

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

A required workflow run is never allowed to remain validation-pending forever. Task-commit discovery ignores later CI-skipped bookkeeping/checkpoint commits so they cannot shadow the newest validation-bearing `[AUTO:<TASK_ID>]` commit. Persisted state that is already bound to a CI-skipped SHA is rebound to that validation-bearing commit on startup/watchdog reconciliation when one exists; otherwise it enters the repair path. If no authoritative run appears for any other reason, `WAIT_ACTIONS_NO_RUN_TIMEOUT_SECONDS` bounds the wait (600s in the VR/localization Portainer stacks) before the same repair path is used. A failed run also triggers a repair turn in the same task chat. Maximum repair attempts: 3. After that, the task is recorded BLOCKED and the controller advances to another independent task.

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

## Localization continuous production + independent batch QA

When `LOCALIZATION_PARALLEL=true`, localization no longer serializes C behind completion of an A/B production pair.

1. Lane A continuously produces the odd-index shard. After its exact durable task commit exists, the slot becomes available for the next A task immediately; A does not wait for a per-producer Actions Gate.
2. Lane B does the same for the even-index shard and also does not wait for a per-producer Actions Gate.
3. Each successful A/B task result is appended to persistent `qa_pending` as an immutable `TASK_ID + RESULT_SHA` input. Production does not wait for C.
4. Lane C is an independent QA consumer. It coalesces up to `LOCALIZATION_QA_BATCH_SIZE` producer results (default 4) for up to `LOCALIZATION_QA_COALESCE_SECONDS` (default 30s), reviews them in one task, reconciles shared state once, and its single commit is the only Actions Gate that consumes a runner for that batch.
5. QA de-duplication key is the exact producer `TASK_ID@RESULT_SHA`. The C prompt additionally requires heavy source/DDS/visual checks to be reused for identical source SHA + candidate SHA + QA-contract fingerprints.
6. A/B must skip candidates still awaiting C QA unless C later records `REWORK_REQUIRED` or the relevant fingerprint changed.
7. A C failure never stops A/B production. Exhausted C batches move to `qa_blocked` for later diagnosis while producers continue.
8. On restart, persisted completed A/B tasks are migrated into `qa_pending`; existing in-flight lanes are preserved.

This model allows QA backlog to grow temporarily without reducing production throughput to zero.


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
- distinct-slot send gap: 15s
- localization same-slot next-task send gap: 15s
- localization slot dedup: 30s
- C QA batch size: 4 producer results
- C QA coalesce window: 30s
- scheduler heartbeat: 15s
- active-generation busy-stall protection: 30m
- explicit rate-limit backoff: 90/180/300/600s
- generic Retry: at most 2 controlled clicks, then same TASK_ID rolls over to a fresh project chat

On startup, persisted nonterminal queue records are reconciled. WAIT_ACTIONS poll guards are cleared so the next queue cycle checks the stored GitHub Actions run ID directly. A failed terminal run retries the same TASK_ID while retry budget remains, after refreshing the current target-branch HEAD.

When redeploying in Portainer, retain the existing localization /data volume so persisted W00018 state can be reconciled instead of discarded.


### Persisted WAIT_ACTIONS task-commit rebinding

On localization stack restart/redeploy, a persisted lane can still contain the result SHA from an older failed attempt even though a newer commit with the same `[AUTO:TASK_ID]` already exists on `korean-localization-clean`.

The controller now force-refreshes branch history during startup reconciliation and rebinds every persisted `WAIT_ACTIONS` record to the newest durable commit carrying that exact TASK_ID. When the SHA changes it clears the stale gate-run binding/status/jobs metadata before Actions discovery. The watchdog repeats this rebinding for stale or still-pending startup records, so an old failed attempt cannot pin a producer lane after redeploy.



### C-batch-only Actions validation

Localization producer A/B commits do not wait for individual GitHub Actions jobs. Their durable task records remain `automation_validation=PENDING` with `validation_mode=C_BATCH_GATE`, and the controller immediately queues the immutable TASK_ID@RESULT_SHA for C and releases that producer slot.

The localization workflow skips its runner-backed validate job for A/B AUTO commits. A C AUTO commit runs the one real batch Gate. That Gate validates the C reconciliation and the exact producer SHAs declared in the C batch. This reduces hosted-runner demand while keeping producer commits immutable and traceable.



### Candidate-completion-first production

Localization A/B no longer use preflight/work-order count as the main throughput target.

- C-accepted `RENDER_READY` assets are completed to an actual Korean DDS candidate before unrelated preflight expansion.
- `ONE_STAGE_TO_RENDER` assets are advanced through the missing deterministic stage and, when inputs remain safe, rendered in the same producer invocation.
- Baseline/slant/style measurement alone is not a reason to split another preflight-only task; measure and render in the same task.
- If a ready asset becomes fail-closed, producers try the next ready asset in their shard before opening new preflight.
- New preflight-only expansion is permitted only when the shard has no runnable RENDER_READY/ONE_STAGE_TO_RENDER asset, and is limited to one batch before the next completion attempt.
- C classifies accepted pre-generation work by readiness when possible and orders shared next-actions candidate-first.
- QA strictness is unchanged.

This policy is also enforced by the live Git localization contract, so it takes effect for newly dispatched work even before the N100 stack is redeployed. Pull/redeploy the localization Portainer stack to bake the updated controller prompts into the running image.
