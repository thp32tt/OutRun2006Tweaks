## 2026-10-13 DX9Ex FEATURE-SIZED QUEUE AND TERMINAL GATE (ACTIVE)

From `CONVERSION-DX9EX-00772`, dispatch one coherent functional outcome per TASK_ID: complete #119 Quest3 adaptive HUD + main menu aspect + ESC scale/position + F11 legibility and regression matrix as one active FEATURE_ID/work_key, not multiple separately terminal one-slider/one-anchor tasks. Resume original live claim/TASK_ID through revisions, grouped source/regression checks, final Win32 host/game/package CI, repairs and C6. Require `feature_contract.feature_id`, integrated goal, >=3 categorized acceptance items across >=2 behavior areas, mapped acceptance_results, and final exact-SHA gate to mark COMPLETE_BUILD_VERIFIED. Intermediate source commits are checkpoints; no per-format/per-widget scoring. DX9Ex Active CI executes `tools/verify_vr_feature_unit_policy.py` to reject new task records without these gates; it does not prove the external Docker dispatcher is updated. Previous tasks 00771 and earlier keep their existing run-record schema. Preserve DX11 parallel writer, frozen DXVK, #119 HMD test UNTESTED and P0-B independent measured performance.

## 2026-10-13 USER OVERRIDE — FEATURE-BATCH VALIDATION AND CI COALESCING (ACTIVE)

The user requires **faster source development without a full compilation for every individual edit**. This section governs all new/retried DX9Ex tasks and supersedes historical micro-commit/per-edit full-build practices; it does NOT relax final acceptance.

1. **One coherent feature batch, not one compile per code change:** recover the live FEATURE_ID/TASK_ID and owner lease; implement related C++/headers/tests together in one scratch/staging tree. Prefer one Git tree + one validation-bearing material commit for a cohesive batch instead of separate pushes for each file, verifier assertion or minor repair. Keep 5-minute durable checkpoints without inventing a new material commit for unchanged code. Preserve one original TASK_ID across retries and rollovers.
2. **While editing:** perform diff/syntax review and changed-area source, targeted unit/mutation/host smoke checks. Do not run full MSVC/Win32/host CI after each intermediate edit. For risky hook, reset, ownership, shared-resource, binary ABI and thread-lifetime changes, use an earlier **targeted** compiler/safety probe when required. Repair a group of related verifier failures locally before the next remote material commit; never weaken negative assertions merely to make a gate pass.
3. **Final integration:** publish all related source + regression updates in a single reviewable final Git commit when practical; never mark a docs-only/status-only commit as the material result. On that exact final validation-bearing SHA require existing DX9Ex Active (including Win32 game/host/package), Domain Isolation, and Full Source Impact checks as applicable, with no reduction in jobs/negative-test coverage. Full Source Impact concurrency now allows one running per ref and **coalesces older pending runs**, avoiding overlapping MSVC static-analysis compiles. A superseded pending SHA is not a PASS; confirm required successful jobs for the retained result SHA.
4. **CI failure:** inspect the concrete failed step first; repair the same TASK_ID in a bounded group, then push a new validation-bearing repair SHA and revalidate **that** SHA. Do not repeat unchanged checks or regenerate a full build on nonmaterial bookkeeping commits. A failing/superseded SHA cannot be called complete. Preserve isolated DX11 writer and frozen DXVK branch.
5. **Runtime:** GitHub build success is not Quest3/VDXR success; mark `RUNTIME_VALIDATION=UNTESTED` until matching HMD evidence. The performance target is **120 FPS when the negotiated display mode supports 120 Hz**, with frametime/p95/p99 evidence required for claims; never hard-code XR refresh. This GitHub policy does not prove the separate Docker queue controller has hot-reloaded; check runtime adoption independently.

## 2026-10-13 ACTIVE USER DISPATCH OVERRIDE — P0-A UI BEFORE NEW MICRO-PERFORMANCE WORK

At C0, load [Issue #119](https://github.com/thp32tt/OutRun2006Tweaks/issues/119), `AGENTS.md`, `docs/DX9EX_AUTODEV_PRIORITY_20261010.md`, and `docs/VR_WORK_QUEUE.json`. Select `DX9EX-QUEST3-RESPONSIVE-UI-20261013` **P0-A** as the next actionable DX9Ex **whole feature**: (1) responsive HUD anchors/scale, (2) main-menu unstretched aspect, (3) separately centered/scaled ESC menu, (4) high-legibility F11 overlay, (5) source/eye aspect and reset negative tests, integrated Win32 full build/packaging + exact-SHA Active and Domain CI, then the user's Quest3/VDXR optical verification. Avoid menu-wide global HUD remapping; preserve approved rank/GOAL/+TIME/lens and stereo visual paths. No DONE from a static audit, task-count bookkeeping or one isolated patch.

**P0-B measured performance stays active concurrently** under its existing live FEATURE_ID/TASK_ID/claim, on nonoverlapping paths. Defer starting new unrelated micro-perf/safety/refactor tasks until the P0-A UI issue is claimed, materially implemented or truly blocked with evidence; do not steal an active writer/lease or halt separate DX11 A development. If P0-A is blocked by a genuine overlapping owner/CI gate, document the blocker and continue existing P0-B productive work. A GitHub policy commit does not prove Docker/Portainer policy hot reload; verify external controller adoption separately. This override supersedes earlier "performance FIRST / HUD P1" ordering; runtime success requires matched Quest3 evidence.

## R84 closed / no repeat dispatch — 2026-10-11 (active override)

Feature `DX9EX:R84_RENDERER_GRAPH` task `CONVERSION-DX9EX-00591` is DONE_BUILD_VERIFIED at target exact material SHA `074768c96c410f0268c084450b0aa8bced38b6c3`. DX9Ex Active #38135749653 (five jobs including full R29–R33 independent Win32 compile/link), Domain #38135749604, and Full Source Impact #38135749550 SUCCESS. The run record status is COMPLETE_BUILD_VERIFIED and `VR_AUTODEV_STATE.json` records SUPERSEDED_BY_DX9EX_FOCUS. A stale queue entry marked READY, or an older section below describing incomplete R84, cannot re-open this already completed feature without new concrete regression evidence. Do not assign duplicate R84 work or score again. Quest3 runtime remains UNTESTED; next independent work is P0 optics/HUD, P2 per-eye and P3 measured FPS.

# Queue Controller Automation Contract

## DX9Ex feature-scoped dispatch and terminal gates — 2026-10-10 21:40 KST (ACTIVE)

**Authority:** The user requires fixing/debugging a whole functional capability per task, not finishing a production job after one trivial edit. This active contract supersedes the historical "one material structure seam per task", "keep changes narrowly scoped", and one-commit-per-feature interpretations below **only where they could terminate an incomplete feature**. Keep risk-bounded diffs and single-writer ownership; do not split feature-level success into micro-task completions.

**Controller selection, before dispatch**
- Fetch latest authenticated GitHub `vr-d3d9ex-focus` HEAD; read `AGENTS.md`, `docs/DX9EX_AUTODEV_PRIORITY_20261010.md`, `docs/VR_WORK_QUEUE.json`, `docs/automation/runs/<TASK_ID>.json`, active work-key claims/lease and exact-SHA Actions. Read a new task only when no conflicting feature owner is live, and only if prior stable feature is terminal or genuinely blocked.
- Stable `FEATURE_ID`/`work_key` is the *functional deliverable*, not the modified file, individual source guard, hook wrapper, test failure, commit or single R-series boundary. A single feature may require multiple reviewable source commits, verifier edits, compile/debug passes and CI attempts; keep one original TASK_ID across these subtasks, retries and 30-minute chat rollovers.
- The currently outstanding R84 structural task is a SINGLE functional acceptance unit: all remaining R33→R32→R31→R30→R29 independent compile/link owners, explicit headers/interfaces, retired `.cpp` textual includes and HEADER_FILE_ONLY declarations, cmake.toml / generated CMakeLists.txt synchronization, full Win32 game/host/chain link, focused regression protection and exact-SHA DX9Ex Active + Domain Isolation success. Do not reopen already APPLIED_EQUIVALENT donor runtime logic or create a new TASK_ID for each extraction.
- At dispatch publish the finite `acceptance_items` (ID, expected behavior, implementation evidence, full-build evidence and validator(s)), `feature_id`, `work_key`, `task_id`, `base_sha`, owned paths, `validation_bearing_result_sha`, `active_claim`/lease and `resume_cursor`. Retain all across ticks; a working repair step stays within the same feature.

**Execution**
- C0 recover -> diagnose full feature and regression history -> C2 implement interdependent changes -> targeted negative RED/GREEN tests -> *complete* Win32 compile/link -> inspect failures and repair -> rebuild until appropriate integration gates PASS -> exact-SHA Active/Domain checks -> persist C6. Never stop merely after an isolated C++/Python fix or `FEATURE_READY`.
- Intermediate labels `FEATURE_READY`, `IMPLEMENTED`, `NEEDS_VALIDATION`, `WAITING_CI`, `PENDING_CONTROLLER_EXACT_SHA`, an intermediate commit, static-only PASS, or a chat rollover are checkpoint-only. A failed exact-SHA CI, missing job, skipped full-chain job or wrong SHA **must not produce terminal DONE**.
- With all deterministic `acceptance_items` green and same `validation_bearing_result_sha` DX9Ex Active / Domain Isolation and required full Win32 gates successful, mark `DONE_BUILD_VERIFIED`. Actual Quest3/VDXR acceptance separately remains `RUNTIME_VALIDATION=UNTESTED` unless matched hardware evidence exists. Do not infer hardware FPS or visuals from CI.
- If any required gate fails, use error logs to fix the SAME feature/TASK_ID; no trivial new FEATURE_ID on retry. If genuinely impossible after bounded repair and capability checks, record `BLOCKED` with exact failing gate/SHA/root cause/next step. A blocked feature is not completed and is not scoreable. Maintain existing cross-lane lease/fencing and idempotent score rules.
- **Known broken example:** `CONVERSION-DX9EX-00590` `dbf6678e543b636858a4cbb1bc8ae847af82597e` was labelled `FEATURE_READY` but DX9Ex Active run `38051682030` failed `R31 StateBlock Apply generation producer` and full-chain compile/host/game/package jobs were skipped. Under this contract it is NONTERMINAL and the authorized owner must resume the same feature for repair, rebuild and validation.

**Runtime deployment boundary:** This GitHub policy is the source document fetched by the external Docker controller. User will deploy/reload independently; a committed document is not evidence the active process has adopted the terminal conditions. Controller implementation MUST incorporate these gates and pass tests for multi-commit same-feature continuation, CI fail→same-ID repair, chat-rollover continuity, same-work-key lease exclusion, and no DONE without full-chain PASS.


## GitHub queue alignment — 2026-10-11 (ACTIVE)

- `DX9EX-P0-VISUAL-COMPOSITION-20261007` is READY for bounded independent source corrections, **not** automatically HMD-accepted. Its former `USER_PRIORITIZED_R84_PRODUCTION_CONVERGENCE` global blocker is retired; independent edits still require a non-overlapping `FEATURE_ID/work_key/active_claim` and must not displace the live `CONVERSION-DX9EX-00591` R84 writer.
- Continue `CONVERSION-DX9EX-00591` through the complete R84 acceptance gate, even when current `FEATURE_READY` is observed. The target's DX9Ex Active and Domain Isolation success must refer to the same final `validation_bearing_result_sha`; skipped full-chain jobs or red verifiers are nonterminal. Changing GitHub policy is **not** a validation-bearing R84 source result and must not substitute its SHA.
- The machine-readable `executionAuthority.dx9exPriority[0]` is `P0_UNRESOLVED_OPTICS_HUD`; FFB v0.2 source and input remain frozen. Quest3/VDXR gates only actual visual/runtime acceptance and DX9Ex live IPC v3 migration, never independent DX11 or non-overlapping C source work. Do not silently auto-unfreeze DXVK.
- Docker downloads GitHub policy but must apply its latest fetched revision each dispatch; a GitHub policy commit alone never proves live-controller deployment. User owns any container redeployment/reload.

## Effective multi-lane dispatch authority — 2026-10-10

- A DX11 Native first-priority ACTIVE on `vr-dx11-native-r71`, C DX9Ex ACTIVE concurrently on `vr-d3d9ex-focus` (50% engineering-effort target), B DXVK FROZEN until explicit user reopening. DX12 reference-only.
- C follows `docs/DX9EX_AUTODEV_PRIORITY_20261010.md`: P0 unresolved user-confirmed optics/HUD correctness (non-overlapping owner/paths) alongside the finite P1 R84 feature, then P2 OpenXR recommended per-eye extent/VD High and P3 measured native performance. Already integrated FFB v0.2 and working gamepad/input are FROZEN absent demonstrated integration regression. Never use the older FFB-first queue label as executable priority. Keep frozen baseline `fcd18ddd89f6dd40a8246fcf8591f086811149f1` untouched.
- HMD/wheel hardware-only acceptance gates do not block other independent C source work, and DX9Ex Architecture v3 live-IPC HMD gate never blocks independent DX11 A. DXVK B must NOT automatically thaw after any DX9Ex gate.
- The 2026-10-07 DX9Ex-only Gate0/R84 selection order below is **historical/non-executable**; Gate0 and inventory were already completed. Keep original architecture/defect evidence, distinct work_keys, exact-SHA validation, GitHub C6 records and no needless CI cancellation.
- Actual external Docker controller deployment, A/C parallel processes and leases require direct runtime confirmation; writing GitHub policy does not prove jobs are running.

## Historical Docker production-controller override — 2026-10-07 (superseded)

The active production automation runs outside ChatGPT in the user's Docker queue controller.

- Before every dispatch, fetch the latest `vr-d3d9ex-focus` HEAD and read `AGENTS.md`, `docs/VR_AUTODEV_STATE.json`, `docs/VR_WORK_QUEUE.json`, and `docs/VR_DX9EX_R84_PRODUCTION_CONVERGENCE.md`.
- Do not rely on historical ChatGPT automation IDs, old clock schedules, a local clone, or an R84 cycle counter to select work.
- HISTORICAL DX9Ex-only order was: recover earlier task -> Gate0 00505 -> R84 seams -> queue. Current C worker uses P0-P3 and must not rerun completed Gate0/inventory.
- `vr-refactor-r84-2000c-20261001` is read-only donor/reference. Never write new work there and never wholesale merge it into focus.
- Historical only: one structure seam per **nonterminal checkpoint/commit**, not one completed task. Feature-level acceptance above overrides micro-task termination. No filler/no-op cycles.
- Keep the existing `[AUTO:<TASK_ID>]` marker and durable run-record requirements.
- A task is not complete while its required exact-SHA gate is red, missing, or belongs to a different SHA.
- Runtime-visible success remains UNTESTED until exact Quest 3/VDXR evidence exists.

This branch is managed by the ChatGPT queue controller.

## Required task record
Every controller-issued task has a TASK_ID. The result commit message MUST include:
`[AUTO:<TASK_ID>]`

Each task must update or add a durable record under `docs/automation/runs/` containing:
- task_id
- target_branch
- base_sha
- result_sha
- automation_validation: PENDING | PASS | FAIL
- runtime_validation: UNTESTED | PASS | FAIL | BLOCKED_RUNTIME
- summary
- evidence
- attempt

## Validation semantics
- Automatic validation and runtime/in-game validation are separate.
- CI success means AUTOMATION_VALIDATION=PASS only.
- If no real HMD/game test was performed, runtime_validation MUST remain UNTESTED.
- Do not claim visual, HMD, GPU synchronization, in-game clipping, or crash-free runtime behavior without actual runtime evidence.
- Runtime-untested work may continue when the next task is independent.
- Runtime-dependent follow-up work must be marked BLOCKED_RUNTIME and skipped in favor of another runnable task.

## Validation-bearing result identity
- A task may have intermediate implementation commits and later bookkeeping/checkpoint commits. The commit that owns the required GitHub Actions Gate MUST be recorded as `validation_bearing_result_sha`; controller validation decisions MUST be made against that exact SHA, not merely the first or latest run observed for the branch.
- Later bookkeeping/checkpoint commits may use CI-skip directives only after the validation-bearing result has completed its required Gate. They MUST preserve the validated `validation_bearing_result_sha` in the durable task record.
- Branch-scoped workflows may intentionally use `concurrency.cancel-in-progress: true`. A `cancelled` run for an older/intermediate SHA that was superseded by a newer push is `SUPERSEDED`, not `AUTOMATION_VALIDATION=FAIL`, and MUST NOT consume a repair attempt by itself.
- Before treating a cancelled Gate as a task failure, the controller MUST inspect the run's `head_sha`, current branch HEAD, the durable `validation_bearing_result_sha`, and any newer Gate run for that validation-bearing SHA. If the exact validation-bearing SHA has a later successful Gate, record PASS and retain the successful run as canonical evidence.
- A cancelled Gate on the current validation-bearing SHA with no superseding commit/run remains unresolved and requires direct inspection; cancellation must never be silently converted to PASS.
- Missing-run recovery is mandatory before timeout failure: if the normal run-discovery path returns no authoritative Backend Conversion Gate, the controller MUST query repository workflow runs for the exact candidate SHA and verify each matching run name, event, head_sha, status, and conclusion. Do not rely only on helpers that return pull-request-associated runs.
- A completed successful Backend Conversion Gate with head_sha exactly equal to the candidate SHA is authoritative evidence even when an earlier poll or wrapper returned no run. Record that exact run and continue instead of consuming another repair attempt.
- A later bookkeeping/checkpoint commit MUST NOT silently replace an already recorded validation_bearing_result_sha. If such a bookkeeping SHA also has a successful Gate, keep that run as auxiliary evidence unless the task explicitly promotes that SHA as a new material/validation-bearing result.
- Only after the exact-SHA fallback search finds no matching Gate and the configured grace window actually expires may the controller classify the condition as a repairable missing-run automation failure.

## Scope
- One modifying task at a time per controller.
- Keep changes narrowly scoped.
- Maximum automatic repair attempts: 3.
- After 3 failed attempts, record the blocker and move to another independent runnable task.
- Never use N100 local clones/worktrees as a project workspace.
- GitHub branch HEAD and Actions are the durable source of truth.

## Completed-task checkpoint SHA regression — 2026-10-08

For `CONVERSION-DX9EX-00547`, the external queue selected documentation-only commit `f478588b4db2e9870bdd49d334a3e9cc590afa51` after E003 already recorded `automation_validation=PASS`. It timed out expecting DX9Ex Active Validation on that bookkeeping commit even though the task record pinned the completed validated material tree `850c522d67252f55a8da6fe296a466e3c43965ae` and its successful run `37710686730`.

**Terminal-idempotency rule:** A retry/rollover for a task with a durable terminal PASS record MUST return the stored `result_sha`, `validation_bearing_result_sha`, `automation_validation`, and `runtime_validation`, without creating another source change, incrementing the point, or polling CI for the current branch HEAD or a newly authored checkpoint SHA. The latest run-record commit is a bookkeeping pointer, not validation-bearing result identity.

**Resolver precedence for a queued attempt:**
1. Read the exact `docs/automation/runs/<TASK_ID>.json` at latest branch HEAD; check task ID and target branch.
2. If `controller_terminal=true` or `status=COMPLETE_BUILD_VERIFIED` with `automation_validation=PASS` and matching exact-SHA successful gate, return the pinned `validation_bearing_result_sha` and stop. Preserve `RUNTIME_VALIDATION=UNTESTED` when hardware testing has not occurred.
3. Otherwise choose `validation_bearing_result_sha`, then `material_result_sha`, never `HEAD` or the most recent bookkeeping response SHA. Verify matching run `head_sha`, workflow name and conclusion before a timeout failure.
4. A bookkeeping/checkpoint commit after PASS may include CI-skip; it MUST NOT replace the already validated material SHA or become the reported RESULT_SHA.
5. When no authoritative matching run exists, distinguish an unvalidated material SHA from a checkpoint-only SHA before consuming a retry attempt. Record the mismatch rather than producing an infinite redispatch loop.

This is a repository-side contract/test oracle. The separate Docker controller implementation must implement these semantics; updating this Markdown does **not** hot-reload or patch a running Docker worker. See `docs/automation/reviews/CONVERSION_DX9EX_00547_E004_RESULT_SHA_AUDIT.md`.


## Chat rollover liveness and duplicate-dispatch guard — 2026-10-08

**Authority and scope.** Applies to direct ChatGPT chat continuation, external Docker/Portainer queue-controller ticks, retries, and A/B/C/D handoffs. A wall-clock tick is only a request to RECONCILE; it is **not** proof the previous chat stopped and must never itself allocate a fresh TASK_ID, reset a lease, replay a completed task, or earn another point. Preserve all backend-specific C0-C6, exact-SHA CI and branch-isolation requirements above.

### Mandatory pre-dispatch decision (before invoking an implementation agent)

1. Fetch the **current authenticated GitHub branch HEAD** and branch-local queue/state, plus `docs/automation/runs/<TASK_ID>.json` for any claimed/in-progress task and exact-SHA Actions evidence. Inspect existing active owner/lease and independent work-item identity. Stale chat text, an expired clock window, missing new commits, and a worker's lack of immediate reply are not terminal evidence.
2. Match by both stable `TASK_ID` and `work_key` (backend/lane + queue/finding/issue ID + semantic source owner + affected paths/producer where known). Check `conflict_keys` for shared source, test, artifact, queue-state and integration ownership **across slots and AI accounts**. Different TASK_IDs pointing to the same uncompleted work_key must not run concurrently; different backend implementations may proceed only when their ownership is explicitly independent.
3. If a run record is **terminal verified** (required C0-C6 and exact-SHA gate PASS, or applicable branch-specific terminal condition), return the persisted canonical material/validation-bearing SHA, CI ID and result. Mark `ALREADY_DONE`; **no source edit, repeat CI, new TASK_ID for the same work, rollover penalty, or additional score**.
4. If the same work_key is **RUNNING / VALIDATING / WAITING_FOR_CI** with a verified live claim, return `ATTACHED_OR_SKIPPED`. Reuse the same TASK_ID/run record; a scheduler tick must not launch another modifying worker. It may monitor CI or pursue a disjoint read-only review.
5. If a worker is missing, the lease is expired, or progress is ambiguous, enter `RECONCILING`, never instant replacement. Compare durable checkpoints, owner epoch/fencing token, branch ancestry, latest source-diff, exact-SHA jobs/artifacts and last real activity. Resume the SAME TASK_ID and exact next step **only after an atomic remote claim/CAS confirms the prior writer is no longer authorized**. If ownership cannot be proven, report `HOLD_OWNER_UNCERTAIN` and do not race a replacement.
6. If the previous task is explicitly `BLOCKED`, `BLOCKED_RUNTIME` or irrecoverably failed with retry limit reached, preserve its evidence, park it and select only a verified independent runnable item. A retry of a recoverable failure uses the **same TASK_ID** and bounded repair counter; periodic rollover is not an error attempt.
7. A **new** TASK_ID can be allocated only if the prior work item is terminal/released, the queue selection is materially different, conflicting live claims are absent, and the assignment is committed atomically against latest GitHub state. No no-op/status-only work is acceptable as a new production achievement.

### Required observability without fake liveness

- At genuine transitions, persist `task_id, work_key, conflict_keys, owner_id, lease_epoch/fencing_token, state, checkpoint, last_real_activity_at, last_activity_evidence, branch, base_sha, material_result_sha, validation_bearing_result_sha, ci_run_id, resume_cursor, next_action, blockers` in the canonical task/claim state (extend the existing schema; do not create a rival state store). The heartbeat may refresh a live claim only with a separately stored timestamp; it **must not** disguise lack of code/CI progress, create pointless commits or advance the score.
- In a long **interactive chat**, show a short factual progress message near tool/stage boundaries when possible (aim for a visible update within roughly 20–30 seconds when the interface permits). Include TASK_ID, C0–C6 stage, latest verified SHA/CI run, and next action. A long blocking tool call may prevent timely messaging; do **not** promise timed heartbeats or background continuation after the chat stops.
- Report separately `ACTIVE` (verified active claim and recent evidence), `WAITING_CI` (authoritative run), `STALE_UNCONFIRMED` (no reliable owner proof), `BLOCKED`, and `DONE`. Do not infer ACTIVE from a spinner, nor STOPPED merely from no new commit.
- Tests required for the **actual Docker controller implementation** before deployment: concurrent same-work-key dispatch yields one writer; different nonconflicting lanes continue; live worker outlasts multiple timer ticks without duplicate dispatch; expired lease + alive worker cannot double-write; orphan resumes same TASK_ID after fenced takeover; terminal PASS yields `ALREADY_DONE` without CI/score increment; bookkeeping HEAD never replaces validation-bearing SHA; partial C0/C1 stays nonterminal.

**Deployment boundary:** These repository instructions are an authoritative acceptance contract for workers that read them. They do not hot-patch the already running external Docker/Portainer dispatcher. Treat runtime enforcement as `NOT_VERIFIED` until its code, configuration, restart and concurrency tests are independently verified. Do not edit or stop a live controller merely to assert this document is active.
