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