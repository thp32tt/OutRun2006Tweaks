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
- For localization C, `completed/success` finalizes the C batch. Localization A/B do not enter WAIT_ACTIONS after a durable producer commit.
- On `completed` with `failure`, `cancelled`, `timed_out`, `action_required`, or `stale`, capture the exact run URL/conclusion and immediately transition to the next task attempt when `attempt < max_task_attempts`. CI failure increments the task attempt; it MUST NOT consume a conversation rollover.
- If the task already has a durable result commit but its bound run cannot be resolved, re-discover the workflow run by exact `result_sha` + workflow name without cache, bind the resulting run ID, then resume exact-run polling.
- If `WAIT_ACTIONS` remains nonterminal for longer than two normal GitHub poll intervals, force an uncached exact-run refresh and refresh job status before waiting again.
- The watchdog MUST actively recover stalled `WAIT_ACTIONS` slots by performing the uncached exact-run refresh. `watchdog_observe_only` is not sufficient for an Actions-wait stall.
- Conversation rollover remains reserved for stale/missing/expired ChatGPT conversations or missing assistant generation. It is independent from GitHub Actions retry handling.
- A and B are independent continuous producers. A durable task commit releases that producer slot immediately and enqueues its exact TASK_ID + result SHA for C; the producer record remains automation-validation PENDING.
- C consumes the persistent QA backlog independently; C completion or failure never gates A/B dispatch.

## Scope
- Up to two candidate-modifying production tasks may run concurrently only when they are lanes A and B and their claimed queue indices/assets are disjoint.
- Lane C may run concurrently as an independent QA consumer, but it reviews immutable producer RESULT_SHAs and MUST NOT rewrite candidate DDS bytes while producers are active. Candidate defects return to A/B as REWORK_REQUIRED.
- A and B must use stable odd/even queue sharding as the primary anti-duplication mechanism and must refresh GitHub HEAD immediately before target selection and immediately before commit.
- If HEAD changed during a run, re-fetch current state and preserve the other lane's committed work. Never overwrite a newer state/report with a stale snapshot.
- Work stealing across A/B shards is disabled while both production lanes are active concurrently. It is allowed only when the other production lane is confirmed idle/completed and the target is unclaimed after a fresh GitHub check.
- A/B must not modify shared state files. Their commits are lane-local only; C alone reconciles `resume_state.json`, worklog, progress/status, asset_queue and shared queue summaries for the immutable producer results in its current QA batch.
- Producer completion is exact-task-commit based, not branch-HEAD based. A/B do not wait for Actions on that SHA. C batch validation later verifies each immutable producer SHA listed in QA_BATCH_INPUTS.
- Keep changes narrowly scoped.
- Maximum automatic repair attempts: 3 per asset for the same dependency/input fingerprint.
- After 3 failed attempts, record the blocker and immediately move to another independent runnable asset in the same lane/run.
- Do not retry that blocker in later waves until its dependency fingerprint changes (source/candidate bytes, runtime evidence, relevant QA input/contract, or explicit user instruction).
- A/B should batch up to 4 newly created or materially reworked DDS candidates per lane per invocation and MUST produce at least one material deliverable while unfinished graphics work remains.
- Zero-output terminals such as NO_ACTION/BLOCKED_NO_ACTION are invalid while unfinished graphics work remains.
- If no safe DDS rewrite is currently possible, create a material fallback deliverable: resolve a zoom-review classification, create a single-DDS isolation manifest/input set with exact hashes, create new per-element reconstruction metrics/specs, or add deterministic asset-specific rebuild/QA tooling plus new machine-readable output.
- Generic blocker prose, an unchanged task record, timestamps, worklog-only edits, and empty commits do not count as progress.
- Existing runtime-isolation candidates are a separate validation backlog; they block only themselves, not unrelated graphics production.
- C must avoid duplicate/no-op QA commits: review only new TASK_ID@RESULT_SHA inputs, reuse unchanged PASS fingerprints, and do not dispatch an already-consumed QA identity.
- Never use N100 local clones/worktrees as a project workspace.
- GitHub branch HEAD and Actions are the durable source of truth.

## Runtime throughput profile
The current-schema values in `localization/controller_roles.json` are mandatory controller runtime inputs; the controller MUST NOT pin or assume an older schema version.

- Scheduler heartbeat: 15 seconds; >45 seconds is a liveness fault.
- Bound GitHub Actions run polling: 30 seconds, exact run ID, zero nonterminal cache TTL.
- Generic Actions discovery/cache: <=60 seconds and only before run-ID binding.
- Stale `WAIT_ACTIONS`: force exact run + jobs refresh by 75 seconds.
- Empty queue with unfinished work: re-arm within 90 seconds; do not wait for the historical 25-minute watchdog.
- Next-task delay: 15 seconds. A/B independent-slot stagger: 15 seconds.
- A or B durable commit -> same producer lane next-task target transition: <=30 seconds; it does not wait for an individual Actions Gate, the peer producer, or C.
- C consumes up to 4 producer results per batch with a 30-second coalesce window; this wait applies only to QA batching and never pauses producers.
- Localization producer same-slot send gap is 15 seconds and localization slot de-dup is 30 seconds after authoritative terminal completion. Rate-limit backoff 90/180/300/600 seconds begins only after an actual rate-limit signal.
- `active_by_lane` is authoritative. A null top-level active summary is valid only when no lane is nonterminal.
- Runtime state must expose `queue_loop_heartbeat_at`, `last_scheduler_decision_at`, `last_scheduler_decision`, and `blocked_reason`.
- Startup/restart must refresh branch HEAD, clear discovery cache, and reconcile every nonterminal lane from exact GitHub state before dispatch.


## Independent C QA / one-pass optimization
- Queue state persists `qa_pending`, `qa_completed`, and `qa_blocked`; the de-dup identity is exact `TASK_ID@RESULT_SHA`.
- C receives explicit `QA_BATCH_INPUTS` and validates those exact commits even if branch HEAD has advanced.
- Heavy QA is fingerprinted by source/candidate bytes and applicable QA inputs/contract. Existing PASS evidence for an unchanged fingerprint is reused rather than recomputed.
- C reconciles shared state once per batch. If a newer candidate supersedes a reviewed result, C records SUPERSEDED and never overwrites the newer state.
- QA backlog growth is acceptable; producer throughput must not be reduced to zero merely because C is slower.


## C-batch-only hosted-runner policy
- A/B AUTO pushes may create a workflow-run shell, but the runner-backed validate job MUST be skipped server-side; the controller never waits for it.
- Only C AUTO commits consume a Localization Automation Gate runner for normal automation.
- Each C task record MUST enumerate top-level `qa_batch_inputs` and one matching top-level `qa_dispositions` entry per input; before the remote Gate completes its `automation_validation` remains `PENDING`.
- The C Gate validates the current C reconciliation plus the exact historical producer commits with PASS dispositions.
- Producer task records remain `automation_validation=PENDING` until covered by a passing C batch; C's batch record + Gate is the durable validation authority.
- A failed C Gate retries/repairs the C batch and may return only the implicated producer inputs as REWORK_REQUIRED; unrelated producers continue.
