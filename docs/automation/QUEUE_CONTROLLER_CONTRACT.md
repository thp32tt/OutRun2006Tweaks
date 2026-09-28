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

## Scope
- Up to two modifying production tasks may run concurrently only when they are lanes A and B and their claimed queue indices/assets are disjoint.
- Lane C is serialized behind the A/B production wave: it must not start final cross-lane QA against assets that are still being modified by A or B.
- A and B must use stable odd/even queue sharding as the primary anti-duplication mechanism and must refresh GitHub HEAD immediately before target selection and immediately before commit.
- If HEAD changed during a run, re-fetch current state and preserve the other lane's committed work. Never overwrite a newer state/report with a stale snapshot.
- Work stealing across A/B shards is disabled while both production lanes are active concurrently. It is allowed only when the other production lane is confirmed idle/completed and the target is unclaimed after a fresh GitHub check.
- A/B must not modify shared state files while running concurrently. Their commits are lane-local only; C alone reconciles `resume_state.json`, worklog, progress/status, asset_queue and shared queue summaries after both production lanes reach terminal durable results.
- Parallel completion is task-commit based, not branch-HEAD based. The controller must find the commit carrying that lane's exact `[AUTO:<TASK_ID>]` marker and validate Actions for that exact SHA even if the peer lane moved branch HEAD later.
- Keep changes narrowly scoped.
- Maximum automatic repair attempts: 3 per asset for the same dependency/input fingerprint.
- After 3 failed attempts, record the blocker and immediately move to another independent runnable asset in the same lane/run.
- Do not retry that blocker in later waves until its dependency fingerprint changes (source/candidate bytes, runtime evidence, relevant QA input/contract, or explicit user instruction).
- A/B should batch up to 4 newly created or materially reworked DDS candidates per lane per invocation when runnable work exists.
- Existing runtime-isolation candidates are a separate validation backlog; they block only themselves, not unrelated graphics production.
- Do not spend a C barrier on a wave where both lanes have zero new candidate bytes and zero material new evidence.
- Never use N100 local clones/worktrees as a project workspace.
- GitHub branch HEAD and Actions are the durable source of truth.
