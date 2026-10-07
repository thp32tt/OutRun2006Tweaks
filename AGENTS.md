# OutRun2 VR Development Execution Contract

## DX9Ex R84 production-convergence override — 2026-10-07

This is the newest DX9Ex execution authority and overrides older backend-allocation/refactor-cycle text when it conflicts.

- **Canonical production/development branch:** `vr-d3d9ex-focus`.
- **R84 donor/reference branch:** `vr-refactor-r84-2000c-20261001` at recovered donor HEAD `40e998500fc758dd3b078d9df2ecc2a57a19bc5d`. Treat it as read-only design/evidence. Do not continue its cycle counter, merge it wholesale, or develop new runtime behavior there.
- R84's purpose was structural improvement. It is not complete until the still-useful structure is reconciled into `vr-d3d9ex-focus` and exact build/validation gates pass.
- Follow `docs/VR_DX9EX_R84_PRODUCTION_CONVERGENCE.md` and the matching `DX9EX-R84-PORT-*` queue items.
- **Gate 0 comes first:** repair the current CONVERSION-DX9EX-00505 exact-SHA validation failure before introducing structural ports.
- After Gate 0 is green, inventory R84-only abstractions and classify each as `APPLIED_EQUIVALENT`, `PORT_REQUIRED`, `SUPERSEDED`, or `DEFERRED_RUNTIME_RISK`.
- Port only `PORT_REQUIRED` structure, one seam at a time, into current focus. Never raw-merge/cherry-pick the divergent R84 branch.
- Target order: R34/R33 -> R33/R32 -> R32/R31 -> R31/R30 -> R30/R29 -> lower Present/Reset/DirectGPU facades -> CMake/textual-include cleanup.
- Every seam requires a deterministic fail-before/pass-after contract where practical, exact GitHub-hosted compile/link validation, Domain Isolation, and current DX9Ex regression gates before the next seam.
- Preserve current DX9Ex runtime semantics: Reset/ResetEx, StateBlock, DirectGPU/ACK/fence/slot ownership, HUD/XYZRHW/SkyGlow, recenter, effects, protected world stereo, and fail-closed fallback.
- `RUNTIME_VALIDATION=UNTESTED` remains mandatory unless the user actually tests the exact build on Quest 3/VDXR.
- Architecture v3 live migration and downstream DX11/DXVK porting remain downstream of this production-convergence phase and their existing HMD gates.
- The production automation executor is the external Docker queue controller. ChatGPT schedule IDs/cadence are not execution authority; GitHub HEAD + queue + this contract are.

This file defines the default execution model for substantial work in this repository, especially the OutRun2 VR/OpenXR backends and build matrix.

## Core rule

Do not run large review/fix/build/package tasks as one unbounded session. Treat work as resumable, bounded transactions with durable checkpoints. A fresh chat, automation run, or worker must be able to continue from repository state without relying on hidden conversation context.

Before substantial work, read:

- `docs/VR_AUTODEV_STATE.json` — machine-readable source of truth.
- `docs/VR_RUN_STATE.md` — concise human handoff, when present.
- `docs/VR_REVIEW_FINDINGS.md` — cumulative deduplicated findings, when present.
- `docs/VR_HOURLY_REVIEW_LOG.txt` and `docs/VR_BUILD_MATRIX_LOG.txt` when relevant.
- `docs/VR_UPSTREAM_REFERENCES.md` and `docs/VR_REFERENCE_HARVEST.md` when the task touches stereo/HUD/effects/frame identity/backend architecture; treat them as design evidence only and re-verify applicability before implementation.

If the human-readable state files do not exist, create them during the next safe checkpoint.

## Upstream and historical evidence-first rule — HUD / UI / effects

For HUD, menu, rank/position markers, lens flare, shadows, billboards, screen-space effects, camera-dependent effects, or similar visual regressions, do **not** start from broad draw heuristics or a fresh runtime test when precise reverse-engineering evidence already exists.

Use this evidence order before implementation:

1. **Original upstream mod first:** inspect `emoose/OutRun2006Tweaks` and treat its reverse-engineered hooks as the first source map. High-value files include `src/hooks_uiscaling.cpp`, `src/hooks_graphics.cpp`, `src/hooks_bugfixes.cpp`, `src/game_addrs.hpp`, and `src/interpolation.cpp`.
2. **Fork history second:** inspect this fork's historical VR branches, commits, `docs/VR_HUD_SEMANTIC_BASELINE.md`, EXE/HUD inspector artifacts, problem history, and checked-in reverse-engineering maps. Reuse previously isolated producer/call-site knowledge rather than rediscovering it.
3. **Canonical EXE proof third:** re-verify every address/call-site that affects a fix against the pinned canonical OR2006C2C.EXE identity, byte signatures, disassembly/XREF evidence, and `docs/VR_BINARY_CONTRACT.json` or equivalent analyzer output. Upstream addresses are strong reverse-engineering evidence, not permission to assume a different binary is identical.
4. **Exact producer ownership:** map the verified producer/call-site into exactly one intended VR semantic/space policy. Do not replace known exact producers with primitive-count, shader-shape, broad WVP, or queue-wide guesses unless contradictory evidence proves the exact map wrong.
5. **Static regression gate before HMD:** add or extend a deterministic fail-closed verifier that pins the relevant source binding, producer ownership, ordering/lifetime rule, and canonical EXE evidence. The canonical GitHub Actions gate must pass before routine HMD testing.
6. **HMD last:** Quest 3/VDXR testing validates hardware-only visual behavior after the source/disassembly/static contract is coherent. Do not use HMD testing as a substitute for available upstream/disassembly/static analysis. An exception is allowed only for an explicitly documented hypothesis that cannot be distinguished statically; such a build must be labeled diagnostic and runtime validation must remain `UNTESTED` until the user supplies evidence.

Known upstream HUD evidence includes the exact rival-rank `Calc3D2D`/rank-marker hooks, the DispRank/POSITION family, Time Attack/result scroll hooks, gear/rev, ghost-gap, goal-time, heart/fruit/rival HUD, control icons, C2C speech bubbles, GF warning, and slipstream paths. Use `docs/VR_HUD_SEMANTIC_BASELINE.md` for the maintained semantic inventory and exact high-value anchors.

This rule is intended to prevent repeated rediscovery and wasted hardware tests: **upstream source map -> fork historical evidence -> canonical disassembly -> current implementation -> deterministic verifier -> HMD**.

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



## Optional installed skills and GitHub-only execution

Development may be performed entirely through the connected GitHub repository and GitHub Actions. A local development PC, RenderDoc capture, or local OpenXR runtime is not required for source/static/CI progress.

Installed Skills are optional helpers, not dependencies or completion authorities. Use them only when they directly reduce uncertainty or accelerate the current checkpoint:
- `outrun-vr-execution-router` for resume/implementation-first routing;
- `outrun-openxr-lifecycle-validator` for OpenXR session/frame/swapchain/recenter state;
- `outrun-stereo-rendering-auditor` for eye/state/HUD/world-marker correctness;
- `outrun-directgpu-sync-auditor` for shared-resource/copy/wait/ACK ownership;
- `reverse-engineering-github-only` for checked-in EXE/disassembly/map evidence;
- `outrun-vr-runtime-log-analyzer` when user runtime logs are supplied;
- `outrun-github-only-build-gate` and `outrun-durable-task-recorder` for exact-SHA validation and durable completion.

If a Skill is unavailable, unsuitable, or would repeat already-completed analysis, continue with the existing repository workflow. Never stop merely because a Skill or local GUI tool is missing.

A state-reconstruction/review/plan-only response is intermediate whenever authorized runnable work exists. Continue C2 IMPLEMENT -> C3 VALIDATE -> C4 COMMIT -> C6 STATE. Runtime-only conclusions remain `UNTESTED` until user Quest 3/VDXR evidence exists.
