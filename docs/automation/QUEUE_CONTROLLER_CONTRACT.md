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
- When an exact-source validation run is queued or in progress under a same-branch workflow with `cancel-in-progress: true`, do not publish another ordinary state-only commit that would supersede and cancel that validation. Finish validation first. If a durability checkpoint is mandatory before validation can start, use a CI-skipped state-only commit and record the validated ancestor/descendant relationship explicitly.
- A GitHub Actions run cancelled before any step starts solely because a newer same-branch run superseded it is not an automatic-validation failure. Keep `automation_validation=PENDING`, inspect the superseding run, and validate the unchanged source through that exact descendant instead of retrying the cancelled run blindly.

## Scope
- One modifying task at a time per controller.
- Keep changes narrowly scoped.
- Maximum automatic repair attempts: 3.
- After 3 failed attempts, record the blocker and move to another independent runnable task.
- Never use N100 local clones/worktrees as a project workspace.
- GitHub branch HEAD and Actions are the durable source of truth.
