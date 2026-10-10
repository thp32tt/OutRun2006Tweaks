# OutRun2 VR Development Execution Contract

## DX11 first real game frame — latest user directive, 2026-10-10

For DX11 production tasks starting at CONVERSION-DX11-00537, the feature outcome is **R175 unblocked and a real OutRun D3D9 Draw routed to a safely enabled native D3D11 visible game frame**, not more independent WARP/guard/Rxxx tasks. This DX11-specific priority supersedes the generic C2 guidance to commit a small fix and move on. Keep C0-C6, 5-minute GitHub checkpoints, 30-minute chat rollover, source owner/lease isolation, exact-SHA final CI, and RUNTIME_VALIDATION=UNTESTED without actual game/HMD evidence.

First inspect R175 existing owner CONVERSION-DX11-00477; fix the real shader parity bug only after verifiable release/transfer, never bypass or weaken CI. Otherwise continue the disjoint live Draw callsite→resource/shader→D3D11 Draw→visible frame integration in a single feature. Treat individual WARP fixtures as necessary internal evidence only, not completed deliverables. Controlled diagnostic opt-in and DX9Ex fallback are mandatory until real gameplay parity is established. The governing machine-readable acceptance contract is docs/automation/DX11_AUTODEV_EXECUTION_POLICY.json.

## Execution location and N100 disk budget policy — 2026-10-08

This policy applies to all AI agents, chats, scheduled automation and retries working on this branch. It restricts **where** work happens; it does not supersede backend/domain isolation, exact-SHA validation, GitHub-only job contracts or runtime test requirements.

1. **First priority, GitHub:** use the authenticated GitHub connector/API for source of truth, file reads/edits, history, branches, commits and GitHub Actions CI/artifacts. Do not clone to inspect files that the connected GitHub tool can fetch. For conversion jobs explicitly marked GitHub-only, remain GitHub-only.
2. **First priority, ChatGPT-local:** use the ChatGPT ephemeral local runtime for analysis, temporary files, transformations and supporting tests that can run there. Remove disposable local outputs after use. Do not infer that a GitHub-only job permits local Git state as authority.
3. **Second priority, N100:** use N100 only when GitHub/ChatGPT-local cannot do a necessary task, or the task requires an N100-resident running service, user-owned file, hardware or network context. Keep N100 operations lightweight and scoped; avoid repeated large builds, bulk scans, image conversion and storage duplication.
4. **Default-deny new N100 checkouts:** do not run `git clone`, `git worktree add`, duplicate full trees or download HD DDS/large archives to N100 just to investigate or build. An exception requires a documented `N100_EXCEPTION_REASON`, exact user-owned target path, estimated maximum bytes, necessity, and cleanup condition. Reuse an existing checkout if safe rather than create another.
5. **Temporary checkout cleanup:** after a justified N100 exception, remove temporary copies only after checking (a) owner UID of all affected files, (b) `git status --porcelain` is clean, (c) HEAD and any branch-local commits are preserved on authenticated GitHub or explicitly retained, (d) no active process or worktree depends on them, and (e) source/destination are within the approved account workspace. Prefer `git worktree remove` *without force* for linked worktrees. If any condition is uncertain, preserve and report the blocker.
6. **Never delete:** files owned by other users, uncommitted/unpushed work, credentials, source-of-truth asset masters, production Docker volumes, active queues, persistent artifacts or running service dependencies. Do not run blanket `docker system prune --volumes`, `git clean -fdx`, `git reset --hard` or recursive cleanup without specific verified scope.
7. **Storage evidence:** for necessary N100 work record before/after available disk, paths and bytes added/removed, ownership, retained data and cleanup outcome. Prefer GitHub Actions artifacts for validated build outputs over N100 copies; preserve `RUNTIME_VALIDATION=UNTESTED` until actual hardware testing.
8. **No retroactive deletion authorization:** this policy does not itself authorize removing existing worktrees, clones or data. Future cleanup must independently validate every deletion against the safeguards above.


This file defines the default execution model for substantial work in this repository, especially the OutRun2 VR/OpenXR backends and build matrix.

## Core rule

Do not run large review/fix/build/package tasks as one unbounded session. Treat work as resumable, bounded transactions with durable checkpoints. A fresh chat, automation run, or worker must be able to continue from repository state without relying on hidden conversation context.

Before substantial work, read:

- `docs/VR_AUTODEV_STATE.json` — machine-readable source of truth.
- `docs/VR_RUN_STATE.md` — concise human handoff, when present.
- `docs/VR_REVIEW_FINDINGS.md` — cumulative deduplicated findings, when present.
- `docs/VR_HOURLY_REVIEW_LOG.txt` and `docs/VR_BUILD_MATRIX_LOG.txt` when relevant.

If the human-readable state files do not exist, create them during the next safe checkpoint.

## Mandatory checkpoint flow

Use the following sequence by default:

### C0 — RECOVER
- Fetch the current development branch HEAD and every relevant component SHA.
- Read durable state and identify the exact unfinished checkpoint and resume cursor.
- Recover relevant CI runs, artifacts, logs, input hashes, blockers, and frozen package identity.
- Do not repeat completed work when the relevant source/dependency/config hashes are unchanged.

### C1 — REVIEW
- Perform one bounded evidence-driven review batch, normally five genuinely distinct lenses/passes.
- Deduplicate findings against prior evidence.
- Separate confirmed evidence, hypotheses, contrary evidence, and hardware-only validation needs.
- Large review requests such as "review 50 times" mean ten persistent five-pass batches (RB01..RB10), not one monolithic reread and not fifty superficial repetitions.

### C2 — IMPLEMENT
- Apply one small coherent fix set or one isolated experiment at a time.
- Do not mix unrelated risky changes in the same checkpoint.
- Preserve backend isolation and branch safety.

### C3 — VALIDATE
- Run the relevant static checks, regression checks, selector/protocol tests, and changed-input builds.
- Prefer fail-before/pass-after evidence where practical.
- A successful compile alone is not runtime proof.

### C4 — COMMIT
- Commit successful coherent changes to the active development branch with a descriptive message.
- Do not leave validated substantive changes only in ephemeral local state when safe remote publication is possible.
- Never force-publish over unrelated work or a live lease.

### C5 — PACKAGE
- Package only when the current phase requires a candidate.
- Verify actual binary/ZIP contents, manifests, component SHAs, config identity, checksums, selectors, and collectors.
- Frozen evening artifacts remain immutable during user testing.

### C6 — STATE
Before ending any substantial run, update durable continuation state.

At minimum record:
- schema version / run ID
- current checkpoint and status
- resume cursor / exact next action
- branch and integration HEAD
- all relevant component SHAs
- relevant source/dependency/config hashes
- completed review batch IDs
- finding IDs and status
- changed files and commits
- build/test/CI IDs and results
- candidate/artifact hashes
- blockers
- retry count for the same unchanged failure
- timestamp

Use atomic/CAS or equivalent single-writer protection where available.

## Bounded-run rule

A run must not keep expanding simply because more useful work exists. Prefer a complete durable checkpoint over an oversized unfinished session.

If the current batch cannot safely finish in the active execution:
1. persist exact partial status and resume cursor,
2. record what was actually completed,
3. stop cleanly,
4. let the next chat/automation run resume from that point.

Never claim background continuation.

## Failure rule

After two materially distinct failed repair attempts for the same unchanged failure:
- mark the item `BLOCKED`,
- preserve evidence and exact failure signatures,
- update durable state,
- move to independent work on the next run.

New evidence may reopen the item. Do not create unbounded repair loops and do not weaken verification to get a green result.

## Review batching

Use persistent review batch IDs:
- RB01 — full relevant source/build graph
- RB02 — caller/lifetime retrace
- RB03 — regression history
- RB04 — backend isolation
- RB05 — OpenXR / DirectGPU
- RB06 — D3D9 state / WVP / Reset / StateBlock
- RB07 — hot paths / frame pacing / draw amplification
- RB08 — failure paths / cleanup / fallback
- RB09 — build / selector / logging / packaging
- RB10 — adversarial integration review of the actual frozen candidate

Each batch should use five distinct lenses:
1. architecture/integration/build/package/license/regression boundaries
2. ownership/lifetime/synchronization/resource generations
3. stereo correctness (WVP/projection/HUD/sky/effects/recenter/menu/white rank-score/fallback)
4. performance (draw/state/caching/copies/waits/telemetry/XR pacing)
5. adversarial review trying to disprove earlier findings

Do not rerun a completed batch unless a relevant input changed. Mark only affected batches stale.

## Branch and release safety

- Treat `vr-openxr` as stable unless the user explicitly requests modification/merge.
- Use `vr-unified-backends` as the primary integration/development branch unless current durable state says otherwise.
- Preserve the five-mode architecture and explicit backend isolation.
- Record every component SHA used by a package; integration HEAD alone is not package identity.
- Do not silently substitute fallback backends or fake A-F variants.


## DX11 integration-first auto-development (effective from CONVERSION-DX11-00531, 2026-10-10)

This section is an **operative DX11 task-selection and acceptance rule**, overriding the generic "one small coherent fix" advice for choosing independent new DX11 production achievements. It does not relax isolation, C0-C6, exact-SHA GitHub Actions, dormant gameplay Draw, runtime proof, single-writer CAS or other safety rules.

1. Before allocating a NEW DX11 work_key, read `docs/automation/DX11_AUTODEV_EXECUTION_POLICY.json`, `docs/VR_DX11_NATIVE_PLAN.md`, the latest task record and active owner/lease. The existing task 00530 is grandfathered; do not restart or steal it. Prefer a complete mono D3D9-command-to-D3D11-WARP-draw-to-pixel vertical slice over another unrelated per-state guard.
2. Prioritize the R175 known independent WARP blocker **only when its owner is released or safely fenced**. While it is actively owned or blocked without new evidence, select a nonconflicting path that connects at least two real producer-to-consumer components. Do not reopen 00477 or duplicate R175 ownership on another task ID simply to satisfy priority.
3. For every new DX11 task >=00531, add `development_strategy` to its durable run record before the validation-bearing commit: `work_class`, `milestone_id`, `integration_path` (>=2 connected stages), `batch_components` (>=2 substantive components), `acceptance_proof` (positive GPU/source proof, negative regression, component integration), `conflict_keys`, and `full_gate_plan=one_validation_bearing_sha`. For blocker/safety/CI work add concrete `blocking_evidence`.
4. Reject new independent tasks that only add one readiness flag, one defensive guard, a static test string, one compile, bookkeeping, or a review; allow a safety repair only with a reproducible failure and explicit integration/unblocking proof. Complete one cohesive source+test+integration batch before scheduling its final exact-SHA full Gate; lightweight static and targeted WARP checks may run while developing. Do not repeatedly compile every micro-edit.
5. Run `python tools/dx11_autodev_policy.py --check-run docs/automation/runs/<TASK_ID>.json` before publication, and record its result. The DX11 `Backend Conversion Gate` and lightweight workflow recheck the newest task from this threshold; do not delete/skip either gate. A scoped WARP PASS with inherited R175 Gate FAIL is `SCOPED_PASS/FULL_GATE_FAIL`, not automation PASS, and gets no score. Keep `RUNTIME_VALIDATION=UNTESTED` absent a genuine HMD/game test.
6. Do **not** enable native gameplay Draw or intercept extra live hooks until explicit production admission and Quest 3/VDXR parity evidence. DX9Ex remains protected. If an external Docker/Portainer controller does not consume this policy, mark its runtime adoption NOT_VERIFIED: repository policy does not silently hot-patch the running controller.

## Backend development priority override — 2026-09-29

This section is the current backend-allocation policy and overrides older backend-priority text elsewhere in this repository when the two conflict.

- **DX11 Native is the primary implementation/performance lane** (nominal engineering allocation about 50%).
- **DXVK is the secondary implementation/performance lane** (nominal engineering allocation about 40%) and remains isolated until exact-build Quest 3/VDXR evidence is available.
- **DX9Ex is maintenance/reference only** (normally <=10%). Do not spend autonomous cycles on new DX9Ex performance tuning or feature expansion. Keep it as the protected visual/regression baseline and fallback; change it only for a critical crash/regression, a deterministic baseline verifier, or work strictly required to compare/unblock DX11/DXVK.
- **DX12/D3D9On12 is frozen/reference-only.** Do not autonomously implement, build, package, optimize, or promote it unless the user explicitly reopens that lane.
- Distribution performance work must target hardware below the development RTX 4070. Do not claim a minimum GPU until measured; prioritize scalable PERFORMANCE/BALANCED/QUALITY profiles, frame-time stability, transport/copy/wait reduction, and 72 Hz viability on lower-tier hardware.
- Single-pass/multiview remains a later optimization candidate only after graphics, lifecycle, selector and two-pass runtime gates are stable.
- Build/CI success is not runtime or low-end performance proof. Quest 3/VDXR exact-build evidence remains required for visual, pacing and performance claims.
- Stale queue/history text that still describes active DX9Ex performance or DX12 development must not create new autonomous work; preserve it as history until explicitly reconciled.


## HDR / floating-point render pipeline design

For DXVK/DX11 work that touches render-target formats, exposure/SkyGlow preservation, post-processing, tone mapping, color spaces, reflection surfaces, or final OpenXR color output, read `docs/VR_HDR_RENDER_PIPELINE_DESIGN.md` before implementation.

Key constraints: preserve restored Xbox exposure/SkyGlow semantics; use selective provenance-driven FP16 promotion rather than blanket render-target upgrades; keep reflection/UI/depth/transport surfaces deny-by-default; tone-map the Quest 3/VDXR path exactly once; and keep runtime claims `UNTESTED` until matching HMD evidence exists. The design document does not authorize native draw-path activation or relax any branch-local conversion gate.

## Interactive chat default

When a user asks to review, fix, build, package, or continue this OutRun2 VR project in chat, follow this contract automatically.

For long tasks:
- resume from repository state first,
- work in C0-C6 checkpoints,
- surface completed checkpoints as soon as they exist,
- persist enough state that a later chat can continue without the previous transcript,
- do not restart completed unchanged work.

User-provided runtime logs and Quest/VDXR tests remain the authority for hardware-only behavior; offline evidence must be labeled accordingly.


## Mandatory logging for direct chat/manual writes

The durability rules apply to **every production write path**, not only scheduled automation.

When ChatGPT/Codex or a human-driven chat directly edits, commits, builds, packages, or integrates production VR code/config/workflows:

1. Treat the writer as a D-equivalent production writer for that transaction and follow C0 -> C6.
2. At C0 read:
   - `docs/VR_REGRESSION_KNOWLEDGE.json`
   - `docs/VR_PROBLEM_HISTORY.md`
   - GitHub Issue #13 (runtime problem/regression ledger) when diagnosing or fixing a runtime symptom
   - GitHub Issue #14 (production change ledger) for the append-only change record
3. Before implementation, compare the intended changed paths/hypothesis against historical regression `riskPaths`, triggers and symptom fingerprints.
4. After each coherent production commit, append an Issue #14 event with:
   `sourceMode=CHAT_DIRECT`, KST timestamp, base SHA, result SHA, summary, changed paths, reason, related finding/regression keys, validation, runtime-test requirement and exact next action.
5. If the change reopens, fixes, mitigates or validates a runtime problem, also:
   - update the matching case in `docs/VR_REGRESSION_KNOWLEDGE.json`;
   - update `docs/VR_PROBLEM_HISTORY.md` when durable knowledge changed;
   - append the corresponding event to Issue #13 using the existing stable regression key.
6. Do not create a new regression key for a familiar symptom until the existing history has been checked.
7. A direct-chat fix is not exempt from regression revalidation, state persistence, build evidence or HMD-evidence labeling.

If GitHub issue write capability is unavailable, mark the transaction `PUSH_PENDING/CAPABILITY_BLOCKED` in durable repository state; never claim the ledger was written when it was not.

## Opt-in PC fast test path

The repository has an interactive Windows self-hosted fast-build path in .github/workflows/vr-pc-fast-build.yml and tools/Build-OutRunPCFast.ps1.

- The runner label is outrun-pc. It is expected to be started manually and remain offline outside a user-requested test/fix/retest session.
- Never route scheduled A/N100/B/C/D work, ordinary review work, pull requests, or untrusted code to this runner.
- Only during an explicitly started **evening user runtime test/fix/retest session** may a direct test-fix commit to vr-d3d9ex-focus include the marker [pc-build]. The runner merely being online is not sufficient authorization.
- [pc-build] is a build trigger, not a validation claim. The workflow preserves out/pc-fast incremental build state and writes a local package to Desktop\OutRunTestBuilds\LATEST.
- PC-fast output is PC_FAST_INCREMENTAL_NOT_FINAL_CI. It never advances the protected runtime baseline and never replaces canonical hosted validation or final packaging.
- Outside that evening test session, scheduled A/N100/B/C/D work, daytime/manual development, review, CI validation, packaging and ordinary direct-chat edits must not use [pc-build]. When the evening session ends, stop using [pc-build] immediately so the user's PC remains uninvolved.



## Controller conversion TASK completion override — 2026-10-02

For controller-dispatched DX11/DXVK conversion tasks, the normal task boundary is **one selected work item through the complete C0→C6 pipeline**, not one review/checkpoint.

- C0 RECOVER, C1 REVIEW, C2 IMPLEMENT, C3 VALIDATE, C4 COMMIT, C5 PACKAGE (or explicit reasoned NOT_REQUIRED), and C6 STATE must all be represented in the current TASK run record before normal release.
- C0-only recovery, C1-only review, plan/status text, state-only commits, and single checkpoint commits are nonterminal. Continue the same TASK_ID.
- C2 requires substantive repository work outside task/state bookkeeping: source, tool, test, workflow, or disassembly-evidence implementation. If runtime hardware is unavailable, continue independent GitHub-only static/source/disassembly/CI work.
- C3 must record validation evidence for the C2 work. Build/CI evidence is not Quest 3/VDXR runtime proof; runtime may remain UNTESTED.
- C5 may be NOT_REQUIRED only with an explicit reason.
- C6 must persist durable continuation state and an exact next action.
- docs/automation/runs/<TASK_ID>.json uses conversion pipeline schema 2 and is controller completion evidence.
- Partial C0→C6 checkpoints exist for interruption/recovery only and do not satisfy normal TASK completion.
- After the full-pipeline result passes its exact-SHA Backend Conversion Gate, the controller should release that TASK and immediately continue with the next independent work item in the same backend lane.

This branch-local override narrows the general bounded-run rule: boundedness still applies inside each stage, but it must not be used to stop normally after C0/C1 or after a bookkeeping checkpoint while independent implementation work remains.
## DX11 conversion-branch state override

This branch is a dedicated conversion lane. Before substantial work, read `docs/CONVERSION_LANE_STATE.json` after fetching the current GitHub HEAD.

For this branch, the precedence is:
1. current GitHub HEAD;
2. `docs/CONVERSION_LANE_STATE.json`;
3. the current durable `docs/automation/runs/<TASK_ID>.json`;
4. this `AGENTS.md`;
5. inherited/historical `docs/VR_AUTODEV_STATE.json`.

The inherited VR_AUTODEV_STATE may contain older DX9Ex/global project policy. It must not overwrite current DX11 conversion-lane status or priority.

Development is GitHub-only. Missing local PC, RenderDoc, local OpenXR runtime, or an installed Skill is not a blocker for repository source/static/disassembly/GitHub Actions work. Installed Skills are optional helpers only and never completion authority.

A stable assistant response that only reconstructs state, reviews, or describes the next step is not task completion. Continue the same TASK_ID to durable repository work/commit; runtime-only claims remain UNTESTED until user Quest 3/VDXR evidence exists.
