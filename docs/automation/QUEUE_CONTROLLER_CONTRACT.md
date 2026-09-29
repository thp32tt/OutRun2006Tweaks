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

## Controller runtime recovery and WAIT_ACTIONS liveness
- `WAIT_ACTIONS` is a transient controller state, never a terminal state and never a reason to stop queue progression indefinitely.
- Once a lane has a concrete `gate_run.id`, the controller MUST poll that exact GitHub Actions run by run ID. Cached workflow-run discovery/list responses are non-authoritative after a run ID is bound.
- Exact run-by-ID status MUST bypass the generic Actions cache. A cached `queued`/`in_progress` value MUST NOT override a fresh exact-run response.
- Nonterminal Actions state may be cached only for discovery before a run ID is known. After binding, the effective nonterminal cache TTL is zero.
- On `completed/success`, finalize the lane as PASS and continue the wave state machine.
- On `completed` with `failure`, `cancelled`, `timed_out`, `action_required`, or `stale`, capture the exact run URL/conclusion and immediately transition to the next task attempt when `attempt < max_task_attempts`. CI failure increments the task attempt; it MUST NOT consume a conversation rollover.
- If the task already has a durable result commit but its bound run cannot be resolved, re-discover the workflow run by exact `result_sha` + workflow name without cache, bind the resulting run ID, then resume exact-run polling.
- If `WAIT_ACTIONS` remains nonterminal for longer than two normal GitHub poll intervals, force an uncached exact-run refresh and refresh job status before waiting again.
- The watchdog MUST actively recover stalled `WAIT_ACTIONS` slots by performing the uncached exact-run refresh. `watchdog_observe_only` is not sufficient for an Actions-wait stall.
- Conversation rollover remains reserved for stale/missing/expired ChatGPT conversations or missing assistant generation. It is independent from GitHub Actions retry handling.
- After both A and B reach durable terminal PASS states for the same wave, dispatch C without waiting for either chat to expire. After C PASS, start the next A+B wave.

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
- A/B should batch up to 4 newly created or materially reworked DDS candidates per lane per invocation and MUST produce at least one material deliverable while unfinished graphics work remains.
- Zero-output terminals such as NO_ACTION/BLOCKED_NO_ACTION are invalid while unfinished graphics work remains.
- If no safe DDS rewrite is currently possible, create a material fallback deliverable: resolve a zoom-review classification, create a single-DDS isolation manifest/input set with exact hashes, create new per-element reconstruction metrics/specs, or add deterministic asset-specific rebuild/QA tooling plus new machine-readable output.
- Generic blocker prose, an unchanged task record, timestamps, worklog-only edits, and empty commits do not count as progress.
- Existing runtime-isolation candidates are a separate validation backlog; they block only themselves, not unrelated graphics production.
- C must also avoid no-op barrier commits: if invoked without new candidate bytes, perform at least one material backlog action or do not dispatch C.
- Never use N100 local clones/worktrees as a project workspace.
- GitHub branch HEAD and Actions are the durable source of truth.
