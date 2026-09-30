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

## GitHub access and permission classification
- Repository access MUST be determined from the authenticated GitHub repository metadata, not inferred from a failed file lookup, missing run record, unsupported endpoint, or an unavailable local/N100 workspace.
- For `thp32tt/OutRun2006Tweaks`, a fresh repository permission response with `permissions.push=true` (or `maintain=true` / `admin=true`) is authoritative evidence that direct branch writes are available to the worker.
- HTTP 404 for an expected path means PATH_OR_REF_NOT_FOUND unless a fresh repository permission check independently proves access loss. It MUST NOT be reported as `GITHUB_PERMISSION_DENIED`.
- Unsupported connector/API operations, stale blob SHA conflicts, branch-HEAD races, validation failures, and rate limits MUST retain their specific failure class and MUST NOT be collapsed into a permission error.
- Before stopping a localization lane for alleged GitHub write denial, refresh repository permissions and branch HEAD. Stop for permission denial only when the authenticated permission check shows no push/maintain/admin capability or an actual write returns an authorization-specific 401/403 after refresh.
- When permissions are valid, recover the lane from current GitHub HEAD and continue incomplete work; do not create an alternate repository, branch, clone, or worktree.

## Dispatch-time schema freshness gate
- Before every initial dispatch, retry, and conversation rollover, fetch current `localization/controller_roles.json` from the latest `korean-localization-clean` HEAD.
- The generated prompt MUST carry `CONTROLLER_SCHEMA_VERSION` and `CONTROLLER_CONFIG_BLOB_SHA` from that exact fetch. A worker MUST refresh current Git HEAD/config when either token is missing or stale; historical odd/even or two-producer instructions are non-authoritative.
- The controller MUST NOT reuse a cached prompt across a config blob change. Retry/rollover prompts inherit TASK_ID/attempt state but regenerate policy directives from current Git.
- Authenticated GitHub connector/API access is the only authority for repository permission preflight. Public web search miss/upstream-only results MUST NOT stop a lane.

## Controller runtime recovery and WAIT_ACTIONS liveness
- `WAIT_ACTIONS` is a transient controller state, never a terminal state and never a reason to stop queue progression indefinitely.
- Once a lane has a concrete `gate_run.id`, the controller MUST poll that exact GitHub Actions run by run ID. Cached workflow-run discovery/list responses are non-authoritative after a run ID is bound.
- Exact run-by-ID status MUST bypass the generic Actions cache. A cached `queued`/`in_progress` value MUST NOT override a fresh exact-run response.
- Nonterminal Actions state may be cached only for discovery before a run ID is known. After binding, the effective nonterminal cache TTL is zero.
- For localization C, `completed/success` finalizes the C batch. Localization A/B/E do not enter WAIT_ACTIONS after a durable producer commit.
- On `completed` with `failure`, `cancelled`, `timed_out`, `action_required`, or `stale`, capture the exact run URL/conclusion and immediately transition to the next task attempt when `attempt < max_task_attempts`. CI failure increments the task attempt; it MUST NOT consume a conversation rollover.
- If the task already has a durable result commit but its bound run cannot be resolved, re-discover the workflow run by exact `result_sha` + workflow name without cache, bind the resulting run ID, then resume exact-run polling.
- If `WAIT_ACTIONS` remains nonterminal for longer than two normal GitHub poll intervals, force an uncached exact-run refresh and refresh job status before waiting again.
- The watchdog MUST actively recover stalled `WAIT_ACTIONS` slots by performing the uncached exact-run refresh. `watchdog_observe_only` is not sufficient for an Actions-wait stall.
- Conversation rollover remains reserved for stale/missing/expired ChatGPT conversations or missing assistant generation. It is independent from GitHub Actions retry handling.
- A, B, and E are independent continuous producers. A/B/E durable task commit releases that producer slot immediately and enqueues its exact TASK_ID + result SHA for C; the producer record remains automation-validation PENDING.
- C consumes the persistent QA backlog independently; C completion or failure never gates A/B/E dispatch.

## Scope
- Up to three candidate-modifying production tasks may run concurrently in lanes A, B, and E when their claimed queue indices/assets are disjoint.
- Lane C may run concurrently as an independent QA consumer, but it reviews immutable producer RESULT_SHAs and MUST NOT rewrite candidate DDS bytes while producers are active. Candidate defects return to the owning A/B/E producer as REWORK_REQUIRED.
- A/B/E must use stable modulo-3 queue sharding (`asset_queue.index % 3`: A=0, B=1, E=2) as the primary anti-duplication mechanism and must refresh GitHub HEAD immediately before target selection and immediately before commit.
- If HEAD changed during a run, re-fetch current state and preserve the other lane's committed work. Never overwrite a newer state/report with a stale snapshot.
- Work stealing across A/B/E shards is disabled while peer production lanes are active concurrently. It is allowed only when the owning peer production lane is confirmed idle/completed and the target is unclaimed after a fresh GitHub check.
- A/B/E must not modify shared state files. Their commits are lane-local only; C alone reconciles `resume_state.json`, worklog, progress/status, asset_queue and shared queue summaries for the immutable producer results in its current QA batch.
- Producer completion is exact-task-commit based, not branch-HEAD based. A/B/E do not wait for Actions on that SHA. C batch validation later verifies each immutable producer SHA listed in QA_BATCH_INPUTS.
- Keep changes narrowly scoped.
- Maximum automatic repair attempts: 3 per asset for the same dependency/input fingerprint.
- After 3 failed attempts, record the blocker and immediately move to another independent runnable asset in the same lane/run.
- Do not retry that blocker in later waves until its dependency fingerprint changes (source/candidate bytes, runtime evidence, relevant QA input/contract, or explicit user instruction).
- A/B/E should batch up to 4 newly created or materially reworked DDS candidates per lane per invocation. While unfinished localizable graphics work remains, a non-DDS material deliverable is only a fallback when a fresh post-evidence scan proves no candidate-completion path is runnable.
- Before dispatch/selection, the controller MUST consume explicit render handoffs from the latest producer/C evidence (`RENDER_READY`, `KOREAN_RENDER_NEXT`, `CLEAN_PLATE_READY...KOREAN_RENDER_NEXT`, or equivalent) ahead of unrelated preflight or runtime-isolation fallback. A C-accepted render-next handoff is sticky until a candidate is attempted or a new deterministic blocker is recorded.
- If an A/B/E invocation itself creates the final prerequisite and reaches render-ready, it MUST continue in that invocation rather than relying on a future queue cycle.
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
- Next-task delay: 15 seconds. A/B/E independent-slot stagger follows current `controller_roles.json`; do not pin a historical value.
- A, B, or E durable commit -> same producer lane next-task target transition: <=30 seconds; it does not wait for an individual Actions Gate, the peer producer, or C.
- C consumes up to 4 producer results per batch with a 30-second coalesce window; this wait applies only to QA batching and never pauses producers.
- Localization producer same-slot send gap and slot de-dup use the current values in `controller_roles.json` after authoritative terminal completion. Rate-limit backoff 90/180/300/600 seconds begins only after an actual rate-limit signal.
- `active_by_lane` is authoritative. A null top-level active summary is valid only when no lane is nonterminal.
- Runtime state must expose `queue_loop_heartbeat_at`, `last_scheduler_decision_at`, `last_scheduler_decision`, and `blocked_reason`.
- Startup/restart must refresh branch HEAD, clear discovery cache, and reconcile every nonterminal lane from exact GitHub state before dispatch.



## Producer pre-gate / rework-loop reduction
- A/B/E MUST run `python tools/localization/verify_producer_pregate.py <changed machine-readable QA JSON...>` after candidate self-QA and before publishing a candidate result when the current task creates or materially reworks Korean graphics.
- This pre-gate is local/read-only and MUST NOT modify shared state, queue state, candidate DDS bytes, peer-lane files, or wait for GitHub Actions. A failure returns only that producer candidate to immediate in-lane repair; it MUST NOT pause peer producers or C.
- The pre-gate mirrors the recurring strict-C rejection classes that are deterministically knowable before submission: zero-pixel containment/protected/alpha metrics, generation-v2 evidence, signed-slant PASS evidence, and forbidden flattened-raster shrink/trim/Lanczos-style repair markers.
- Passing this producer pre-gate is not C approval and not runtime validation. C remains the independent authority for batch disposition, and `RUNTIME_VALIDATION=UNTESTED` remains mandatory until a real game test occurs.
- Existing immutable producer results already queued for C are not retroactively blocked by this rule; apply it to new/materially reworked producer results after this contract revision.

## Independent C QA / one-pass optimization
- Queue state persists `qa_pending`, `qa_completed`, and `qa_blocked`; the de-dup identity is exact `TASK_ID@RESULT_SHA`.
- C receives explicit `QA_BATCH_INPUTS` and validates those exact commits even if branch HEAD has advanced.
- Heavy QA is fingerprinted by source/candidate bytes and applicable QA inputs/contract. Existing PASS evidence for an unchanged fingerprint is reused rather than recomputed.
- C reconciles shared state once per batch. If a newer candidate supersedes a reviewed result, C records SUPERSEDED and never overwrites the newer state.
- QA backlog growth is acceptable; producer throughput must not be reduced to zero merely because C is slower.


## C-batch-only hosted-runner policy
- A/B/E AUTO pushes may create a workflow-run shell, but the runner-backed validate job MUST be skipped server-side; the controller never waits for it.
- Only C AUTO commits consume a Localization Automation Gate runner for normal automation.
- Each C task record MUST enumerate top-level `qa_batch_inputs` and one matching top-level `qa_dispositions` entry per input; before the remote Gate completes its `automation_validation` remains `PENDING`.
- The C Gate validates the current C reconciliation plus the exact historical producer commits with PASS dispositions.
- Producer task records remain `automation_validation=PENDING` until covered by a passing C batch; C's batch record + Gate is the durable validation authority.
- A failed C Gate retries/repairs the C batch and may return only the implicated producer inputs as REWORK_REQUIRED; unrelated producers continue.

## Throughput correction v16 — DDS completion first

Effective immediately, throughput is measured in deployable Korean DDS candidates and C static-QA production completions, not task count, preflight count, guard count, or bookkeeping commits.

- A/B/E target **2 candidate DDS outputs per invocation by default** when runnable completion-tier work exists. They may batch **up to 4** compatible family/template assets; a genuinely complex atlas may use a target of 1.
- After one candidate succeeds, continue to the next ready asset in the same invocation while the lane budget and safe runnable work remain. Do not terminate merely because one DDS was produced.
- `DIRECT_REWORK_REQUIRED`, explicit render-next handoffs, `RENDER_READY`, `ONE_STAGE_TO_RENDER`, and existing-candidate rework are completion tiers. If any completion-tier item is runnable in the owning shard, unrelated preflight/source-guard/dependency research MUST NOT be selected.
- Preflight-only work is a fallback only after a fresh full-shard scan proves no completion-tier item is runnable. A preflight result never counts toward DDS throughput.
- The same dependency/input fingerprint may receive at most 3 repair attempts. After the third failure, route it to `EXCEPTION_QUEUE`, record the blocker/fingerprint, and continue independent assets. Retry only after the dependency fingerprint changes or explicit user instruction.
- C prioritizes producer results that contain a new or materially reworked DDS candidate. Preflight/research-only producer results are secondary and MUST NOT delay a candidate-bearing C batch.
- Heavy C QA remains fingerprint-deduplicated. Reuse unchanged PASS evidence; never rerun expensive checks solely because bookkeeping or task identity changed.
- A current-generation v2 candidate that passes independent C static QA is `PRODUCTION_COMPLETE` even while `RUNTIME_VALIDATION=UNTESTED`. Runtime/in-game validation remains a separate user integrated-test state and is not a production/static-QA completion gate.
- Progress reporting MUST expose at least: `production_complete`, `candidate_awaiting_c`, `runnable_production`, `blocked_exception`, and `runtime_validated`. Do not present runtime-untested production-complete assets as if no graphics production was completed.
- Zero-pixel containment, exact HD-source identity, English-residue rejection, DDS/header/format/mip/alpha/orientation preservation, source-faithful style, and all existing strict visual gates remain unchanged.

The scheduler should optimize the conversion path:
`REWORK/READY -> DDS CANDIDATE -> C STATIC PASS (PRODUCTION_COMPLETE)`
and keep runtime validation as a later independent gate.

## Throughput enforcement v17 — producer batch is a hard invariant

Effective immediately, the v16 candidate target is executable completion policy, not advisory guidance.

- A/B/E normal producer success requires **at least 2 new or materially reworked Korean DDS candidates in the same invocation** whenever a fresh owning-shard scan exposes at least two runnable completion-tier assets.
- Producing one candidate MUST NOT release the lane or terminate the invocation when a second runnable completion-tier asset exists. After every candidate, refresh the owning shard and continue until the target is met or runnable completion work is exhausted.
- A one-candidate result is permitted only as typed `PARTIAL_BATCH` when a fresh owning-shard scan proves fewer than two runnable completion-tier assets remain. The task record must preserve that exhaustion evidence; it is not normal batch success.
- Preflight, source guard, bookkeeping, runtime isolation, or research cannot fill a missing candidate slot and never count toward the batch target.
- Compatible family/template work may continue to 4 candidates. Complex-atlas handling may still use one candidate only when the fresh shard scan proves no second safe runnable completion-tier asset for that invocation.
- C continues candidate-first QA and may consume up to four producer results per batch. Strict static QA thresholds are unchanged.

The enforced producer loop is: `fresh shard scan -> candidate -> rescan -> candidate -> durable result`; only proven shard exhaustion may shorten it.
