# Queue Controller Automation Contract

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

## DX11 auto-work selection and batching gate (effective 00531)

For new DX11 `CONVERSION-DX11-00531` and later runs, **before** assigning an independent task, consult `docs/automation/DX11_AUTODEV_EXECUTION_POLICY.json` and evaluate `python tools/dx11_autodev_policy.py --check-run docs/automation/runs/<TASK_ID>.json`. Persist `development_strategy` with the selected milestone, real source-to-pixel integration path, at least two substantive batch components, positive/negative/integration proofs and conflict owner keys. The canonical material commit must improve the connected path, not merely add a lone readiness guard. Exact-SHA full Backend Conversion Gate and separate scoped GPU checks remain mandatory; never score FAIL as PASS.

The DX11 workflow statically tests acceptance of the highest-numbered run record at the new threshold. Existing 00530 retries/C6 remain grandfathered. Agents must inspect actual owner leases and cannot duplicate the separately blocked R175 owner. Prefer one fast/static + targeted GPU loop per coherent batch and one final full exact-SHA Gate, not repeated full builds on one-line edits. External N100/Docker controller rollout must be verified separately; this repo rule alone does not certify a running dispatcher configuration.
