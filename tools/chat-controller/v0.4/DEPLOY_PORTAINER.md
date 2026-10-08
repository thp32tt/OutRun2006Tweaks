# OutRun Chat Controller v0.4 — Portainer deployment

## Architecture

N100 runs the browser/controller containers. VR jobs may also use N100 local workspaces and Google Drive as auxiliary input, analysis, build, validation, or transport sources; the assigned GitHub branch remains the durable source/output authority.

- VR SSOT: `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`
- Korean localization SSOT: `thp32tt/OutRun2006Tweaks` / `korean-localization-clean`
- For VR jobs, N100 local clones/worktrees and Google Drive are permitted as auxiliary work/transport sources; durable completion still requires the assigned GitHub branch result.
- Each ChatGPT account must have working GitHub read/write access before AUTO_SEND is enabled.

## Portainer Git source

Repository:
`https://github.com/thp32tt/OutRun2006Tweaks.git`

Reference:
`refs/heads/chat-controller-downloads`

> Portainer에서 **Reference를 비워두지 마세요.** 이 저장소의 기본 브랜치는 `master`이며,
> `master`에는 `tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`이 없습니다.
> 따라서 Reference가 비어 있거나 `master`이면
> `Unable to retrieve stack file: Could not get the contents of the file ...` 오류가 발생합니다.
> 저장소는 public이므로 별도 Git 인증이 필요하지 않습니다.

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
5. For VR, confirm N100/Google Drive auxiliary use is allowed while final completion is still recorded on the assigned GitHub branch.

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

For VR, temporary GitHub unavailability does not forbid N100 local workspaces or Google Drive for auxiliary work. Do not claim job completion until the required material result is committed to the assigned GitHub branch.


## Queue mode (v0.5 behavior in v0.4 deployment path)

Both existing Portainer compose paths now run the GitHub-gated queue engine.

### Conversion stack
The existing `docker-compose.portainer-vr.yml` path is retained for compatibility, but its controller mode is now `conversion`.
The VR compose uses `Dockerfile.portainer-vr`, which pins the proven Controller v2 TASK_ID/event queue independently from localization controller changes. Existing A/B state is preserved and slot C is appended when `CHAT_SLOTS=3`.

- lane A: DX11 -> `vr-dx11-native-r71`
- lane B: DXVK -> `vr-dxvk-r71-disasm`
- lane C: DX9Ex improvement -> `vr-d3d9ex-focus`
- DX11/DXVK required workflow: `Backend Conversion Gate`
- DX9Ex required workflow: `DX9Ex Active Validation`
- active priority: C (DX9Ex structural refactor) first, A (DX11) second
- up to two high-priority lanes (C + A) may be active at once
- B (DXVK) is deferred and is only dispatched as fallback when both higher-priority lanes are unavailable
- successful automatic validation advances without allowing a stalled lane to block the other active priority lane
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

## 2026-10-08 — DX11/DXVK implementation-first VR scheduler

Redeploy the **VR** Portainer stack with the exact `chat-controller-downloads` branch files from `tools/chat-controller/v0.4/`. Build the image again (do not just restart the old image). `Dockerfile.portainer-vr` assembles `src-vr-v2/controller.py.part00..03`; the legacy `src/` localization controller is not this VR application.

- A = DX11 Native (first priority); B = DXVK (second primary lane); `CONVERSION_ACTIVE_LIMIT=2` keeps these two lanes in parallel. Existing in-flight C(DX9Ex) work occupies one capacity slot until reconciled; it is not overwritten.
- C = DX9Ex **maintenance only**: `CONVERSION_DX9EX_ENABLED=false` by default, opt in only when a critical regression needs repair (or set `CONVERSION_ONLY_SLOT=C` for a dedicated maintenance run). Previous policy `CONVERSION_DXVK_DEFERRED=true` is retired and must not be carried into the new stack.
- Missing HMD evidence parks runtime promotion as `NEED_HMD_TEST`/`RUNTIME_VALIDATION=UNTESTED`; the agent picks the next independent source implementation inside its lane, retaining TASK_ID/C0-C6, exact-SHA GitHub validation, ownership, and no duplicated task/CI.
- Do not run unchanged HUD 1000/5000 static loops. Source changes use targeted tests + exact-sha CI. Neither a status-only commit nor static-only analysis can be reported as native Draw/DrawIndexed runtime activation.
- Portainer deployment: update/rebuild VR stack from this GitHub branch; preserve named `/data` and `/logs` volumes, saved credentials, browser profile, and existing queue state. After deployment verify `/status`, `conversion_dx11_enabled=true`, `conversion_dxvk_enabled=true`, `conversion_dx9ex_enabled=false`, and `conversion_parallel_running` reports A(DX11)/B(DXVK). Observe new C2 material SHA + successful Gate; do not infer successful runtime rendering without Quest3/VDXR tests.
- This commit updates the GitHub deployment source only. It neither hot-patches nor proves the running Portainer container changed.

## 2026-10-08 — FINAL OVERRIDE: DXVK FROZEN; DX11 Native only

**The user's later explicit directive supersedes the immediately preceding dual DX11/DXVK priority note and every older DX9Ex co-primary policy in this file.** Redeploy only the current `chat-controller-downloads` branch VR stack, rebuilding `Dockerfile.portainer-vr` from GitHub rather than simply restarting its old Docker image.

* A(DX11) is the **only** automatic work lane: `CONVERSION_ONLY_SLOT=A`, `CONVERSION_ACTIVE_LIMIT=1`, `CONVERSION_DX11_ENABLED=true`.
* DXVK B is **FROZEN**: `DXVK_FROZEN=true`, `CONVERSION_DXVK_ENABLED=false`. It must not start, resume or create commits; the controller rejects a misconfigured `CONVERSION_ONLY_SLOT=B` while the freeze is enabled.
* DX9Ex C is **disabled for normal automatic work**: `CONVERSION_DX9EX_ENABLED=false`. Existing B/C active records are moved to persistent `frozen_lane_tasks` on the first reconciled scheduler cycle; they are not deleted, interpreted as successes, or granted new TASK_IDs.
* DX11 must continue **real native implementation** on its own lane even without HMD runtime access. Runtime-only results are `UNTESTED/NEED_HMD_TEST` and block only promotion to runtime verified. No unchanged 1000/5000 static loops, unearned native activation, or state-only progress.
* Keep `outrun_chat_vr_data` and `outrun_chat_vr_logs` volumes and configured browser/session credentials. Verify `/status` shows `dxvk_frozen=true`, `conversion_dx11_enabled=true`, `conversion_dxvk_enabled=false`, `conversion_dx9ex_enabled=false`, `conversion_only_slot=A` and that no slot B/C messages are sent after deployment.
* The GitHub commit only changes redeployable source. Actual Portainer application and Quest 3 runtime behavior are not proved until separately tested.
