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

- memory hard limit: 4 GiB
- memory reservation: 2 GiB
- CPU limit: 1.5
- shared memory: 768 MiB

## Fresh-chat task lifecycle

Queue tasks use one browser page per configured slot, but each **new TASK_ID** replaces that slot's previous completed ChatGPT page with a fresh project chat. Same-TASK retries reuse the current chat until retry/rollover policy requires a replacement. This bounds long-conversation DOM/renderer growth while preserving Git and `/data/state` as the durable state. Localization remains four slots: physical A/B/C/D map to logical A/B/C/E. The scheduler uses missing-worker dispatch fairness so a ready C batch or unthrottled missing producer is filled before active Retry traffic can refresh the global send gap.

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
- physical A -> producer A (`asset_queue.index % 3 == 0`)
- physical B -> producer B (`asset_queue.index % 3 == 1`)
- physical C -> independent batched QA consumer C
- physical D -> logical producer E (`asset_queue.index % 3 == 2`)
- branch: `korean-localization-clean`
- producer A/B/E commits release their lane on durable Git evidence and are validated later by C batch Gate
- C uses `Localization Automation Gate`; runtime validation remains `UNTESTED` until user game testing

### Controller completion rule
A chat response is never completion authority. The controller resolves the durable `[AUTO:<TASK_ID>]` commit first, using normal branch history plus the exact `docs/automation/runs/<TASK_ID>.json` history so high-throughput branches cannot hide an older task beyond the first 100 commits.

- Conversion DX11/DXVK: the validation-bearing task commit must have the exact `Backend Conversion Gate` run and that run must conclude `success`.
- Localization C: the validation-bearing C commit must have the exact `Localization Automation Gate` run and that run must conclude `success`.
- Localization A/B/E: a durable producer commit releases the producer immediately; automatic validation remains pending until C consumes that immutable TASK_ID@RESULT_SHA.
- CI-skipped bookkeeping is never allowed to shadow a validation-bearing commit. If a Gate-required task has only a CI-skipped task commit, it enters bounded repair rather than pretending no commit exists.

Missing Actions-run creation is bounded by `WAIT_ACTIONS_NO_RUN_TIMEOUT_SECONDS=600`. An existing run that remains `queued`/`in_progress` is separately bounded by `WAIT_ACTIONS_MAX_SECONDS=1800`. Failed or timed-out validation retries the same TASK_ID while budget remains. Maximum repair attempts are 3; after that the task is recorded BLOCKED and the queue advances instead of waiting forever.

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

When `LOCALIZATION_PARALLEL=true`, localization no longer serializes C behind completion of an A/B/E production set.

1. Producer A owns `asset_queue.index % 3 == 0`, B owns remainder 1, and logical E (physical slot D) owns remainder 2. Each producer releases immediately after its exact durable task commit; no per-producer Actions Gate is required.
2. Each successful A/B/E result is appended to persistent `qa_pending` as immutable `TASK_ID@RESULT_SHA`. Production does not wait for C.
3. C is an independent QA consumer. It coalesces up to `LOCALIZATION_QA_BATCH_SIZE=4` producer results for up to `LOCALIZATION_QA_COALESCE_SECONDS=60`, reconciles shared state once, and its single commit owns the batch Actions Gate.
4. QA de-duplication uses exact producer `TASK_ID@RESULT_SHA`; unchanged heavy QA evidence may be reused only under the current Git policy fingerprint.
5. A/B/E skip candidates still awaiting C unless C returns `REWORK_REQUIRED` or a relevant dependency/candidate/QA-contract fingerprint changes.
6. E is elastic: pause new E work at `qa_pending >= 16`, resume below 12; A/B remain independent.
7. C failure never stops A/B/E production. Exhausted C batches move to `qa_blocked` while producers continue.
8. On restart, persisted nonterminal lanes are reconciled against Git before UI Retry/busy handling. Durable commits always outrank stale ChatGPT UI state.

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
- localization same-slot next-task send gap: 30s
- localization slot dedup: 30s
- C QA batch size: 4 producer results
- C QA coalesce window: 60s
- scheduler heartbeat: 15s; fatal event-loop heartbeat stall: 300s -> process exit / Docker restart
- active-generation busy-stall protection: 30m -> same TASK_ID fresh-chat rollover instead of infinite WAIT_CHAT
- existing nonterminal Actions-run maximum wait: 1800s
- repeated identical queue exception: 3 cycles -> process exit / Docker restart
- repeated identical watchdog exception: 3 cycles -> process exit / Docker restart
- explicit ChatGPT rate-limit backoff: 90/180/300/600s; Git/Actions reconciliation continues during backoff
- generic Retry: at most 2 controlled clicks, then same TASK_ID rolls over to a fresh project chat

On startup, persisted nonterminal queue records are reconciled against Git before UI recovery. Queue and registry JSON keep last-known-good backups and are restored from backup on primary-file corruption/missing-primary cases; the controller refuses a destructive empty reset when both copies are unreadable. Daily logical-date rollover preserves active slot URLs and send/rate state. A prompt that was already submitted is always represented by an active TASK_ID even when a rate-limit/Retry surface appears immediately after send, preventing orphan work and TASK_ID reuse.

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
