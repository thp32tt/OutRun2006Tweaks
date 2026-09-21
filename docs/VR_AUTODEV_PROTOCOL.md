# OutRun2 VR Four-Role Autonomous Development Protocol

This repository-side protocol matches the four Work scheduled roles. The schedule is external; this file defines durable coordination and ownership.

## Integration target and backend scope

- Integration/production branch: `vr-d3d9ex-focus`.
- Stable `master`, `vr-openxr`, and `wheel-ffb` are never autonomous write targets.
- Reference renderer: native Win32 D3D9/D3D9Ex game + x64 D3D11 OpenXR host.
- DXVK, multiview and DX12/D3D9On12 remain paused until the DX9Ex reference milestone is user-accepted or explicit backend-specific evidence requires work.

## Four-role ownership

### A — ARCHITECTURE REVIEW
- Primary role branch: `vr-d3d9ex-review-a`.
- Reviews architecture, control flow, state/lifetime/reset and cross-subsystem ownership.
- Production runtime source, candidates, build/CI and integration are read-only.
- Persists evidence/checkpoints only; does not rewrite integration state/queue/history.

### B — RENDERING REVIEW
- Primary role branch: `vr-d3d9ex-review-b`.
- Reviews rendering, stereo, HUD, XYZRHW, world/effect semantics and visual fallback.
- Production runtime source, candidates, build/CI and integration are read-only.
- Persists evidence/checkpoints only; does not implement fixes.

### C — PERFORMANCE / OPENXR REVIEW
- Primary role branch: `vr-d3d9ex-review-c`.
- Reviews performance, frame pacing, copies/waits, OpenXR synchronization, shared-texture protocol and testability.
- Production runtime source, candidates, build/CI and integration are read-only.
- Persists evidence/checkpoints only; does not validate or merge production candidates as an owner.

### D — FIX / BUILD / VALIDATE / INTEGRATE
- Sole autonomous writer of production runtime code and consolidated state on `vr-d3d9ex-focus`.
- D alone creates `vr-d3d9ex-candidate/<finding-id>-<run-id>` branches, implements one coherent hypothesis per candidate, runs candidate CI, validates evidence, and integrates accepted candidates.
- Consumes A/B/C review records idempotently and requests/reuses independent post-review evidence when required.
- Two materially different failed fixes for the same unchanged failure => BLOCKED evidence, then move on.
- Owns `docs/VR_WORK_QUEUE.json`, `docs/VR_AUTODEV_STATE.json`, `docs/VR_RUNTIME_FEEDBACK.json`, and `docs/VR_SCHEDULED_RUN_HISTORY.md`.
- Only D freezes/finalizes user test packages.
- Build success is not HMD correctness; hardware-visible conclusions stay NEED_HMD_TEST.

## Resumable checkpoint model

C0 RECOVER -> C1 REVIEW -> C2 IMPLEMENT if role allows -> C3 VALIDATE -> C4 COMMIT if role allows -> C5 PACKAGE if warranted -> C6 STATE

Every run starts from durable GitHub state and exact SHA/config identity. Completed checks with unchanged relevant input hashes are reused.

## Queue states

Allowed central states:
- READY
- IN_PROGRESS
- NEEDS_VALIDATION
- VALIDATED
- NEEDS_POST_REVIEW
- NEED_HMD_TEST
- BLOCKED
- DONE

A/B/C submit evidence; D performs central queue transitions. Stable finding IDs and dependencies must be preserved.

## Candidate WIP limit

At most **3 independent unvalidated runtime candidates** may exist at once. When the cap is reached:
- do not create another runtime candidate;
- validate/fix existing candidates;
- improve deterministic diagnostics/verifiers;
- continue independent source review.

Legacy P1-P4 comparison artifacts do not count when explicitly retired from the current default test policy.

## Evidence levels

- STATICALLY VERIFIED: source/verifier evidence only.
- BUILD VERIFIED: exact candidate build/checks passed.
- USER RUNTIME VERIFIED: matching Quest 3/VDXR package/profile/session evidence.

Never promote visual correctness, stereo alignment, pacing, recenter, sky/effects or HUD placement from build evidence alone.

## Review reuse

Review cache identity is:
`relevant dependency/input hash + subsystem + review lens`

A docs-only commit does not invalidate runtime build evidence. Do not repeat unchanged completed reviews only to consume scheduled time.

## Runtime test minimization

Default evening target is one CORRECTNESS package/profile. Add CONTROL or PERFORMANCE only when required to distinguish a concrete hypothesis; maximum 3 user choices.

Preserve:
- `SkyGlowFactor=1`
- runtime-selected refresh (`TargetRefreshRateHz=0` / equivalent dynamic XR cadence)
- no hard-coded 120 Hz assumption
- no monitor-resolution-as-eye-resolution assumption
- frozen package immutability while the user is testing

## Runtime feedback identity

Normalized runtime evidence belongs in `docs/VR_RUNTIME_FEEDBACK.json` and must identify when available:
- BuildMatrixId
- VariantId
- TestProfile
- SessionId
- source SHA
- config hash
- OpenXR/VDXR refresh and recommended eye size
- log/capture bundle identity
- user-observed startup/stereo/HUD/effects/recenter/pacing results

## Candidate CI contract

`.github/workflows/vr-dx9ex-active.yml` accepts both:
- `vr-d3d9ex-focus`
- `vr-d3d9ex-candidate/**`

Concurrency is branch-scoped so independent candidates do not cancel one another. A candidate build does not authorize integration; C/D still consume actual checks and evidence.

## Durable run records

Every role-run JSON should include:
- schemaVersion
- role
- runId
- startedKst / completedKst
- baseSha
- findingId(s)
- dependency/input hashes
- changed paths (if any)
- candidateSha (D, when created)
- actual CI run/artifact identifiers
- evidence level
- queue proposal
- blockers/retry count
- exact nextAction

D appends one consolidated history entry per consumed run and records the run ID to prevent duplicate import.

## Uploaded runtime bundle ingestion

A standardized runtime ZIP with `ANALYSIS_REQUEST.json` and `AutoAnalyzeOnUpload=true` is sufficient to start runtime analysis without an additional user prompt.

Ingestion order:
1. Validate `BuildMatrixId`, `VariantId`, `TestProfile`, `SessionId`, source SHA, config hash and EXE identity.
2. Correlate the bundle with the frozen/user-tested candidate and current integration history.
3. Analyze available game/host/watchdog/backend logs, HUD trace/semantic coverage, shader fingerprints, captures, dumps and test metadata.
4. Convert concrete evidence into existing finding IDs when possible; new evidence for an existing issue strengthens or reopens that finding instead of creating duplicates.
5. Update runtime-feedback/state only when the evidence identity is unambiguous.
6. Treat any accompanying user description as optional extra evidence. Do not require the user to restate symptoms already inferable from the standardized bundle.

An incomplete bundle is analyzed to the maximum supported extent and marked with explicit evidence gaps rather than being discarded.


## Durable regression knowledge gate

Runtime regressions are durable project knowledge, not chat-only context.

Sources of truth:
- machine-readable registry: `docs/VR_REGRESSION_KNOWLEDGE.json`
- human runbook/history: `docs/VR_PROBLEM_HISTORY.md`
- append-only event ledger: GitHub Issue #13, `[VR] Runtime Problem / Regression Ledger`

### Mandatory C0 recovery behavior

Every A/B/C/D run that can affect diagnosis or integration must load the regression registry before new hypotheses are created. D must additionally:
1. compare the current candidate changed paths and behavior hypothesis with every case's `riskPaths`, `revalidationTriggers`, and `symptomFingerprint`;
2. reuse the existing regression key when the same symptom recurs;
3. recover known-good/known-bad identities, prior root cause, prior fix references and verifier recipe before attempting a new fix;
4. record missing historical data as `NEEDS_RECONSTRUCTION` rather than inventing it.

### Integration gate

A D candidate may not be integrated merely because it compiles or its new finding is fixed. Before integration:
- every triggered historical regression case must have a current revalidation result;
- deterministic/static/build-verifiable checks must pass;
- hardware-visible regressions may remain `NEED_HMD_TEST`, but that state must be explicit and carried into the next frozen CORRECTNESS package;
- a recurrence must increment the existing case recurrence counter and append a `REOPENED` event to Issue #13.

### Fixed/DONE requirements

A regression is not durably FIXED/DONE until the registry contains:
- stable regression key and symptom fingerprint;
- bounded root cause;
- exact fix reference(s);
- affected/risk paths and revalidation triggers;
- deterministic verifier or evidence recipe;
- validation evidence level;
- for runtime-visible behavior, matching USER RUNTIME VERIFIED evidence before final DONE.

### Event persistence

Issue #13 is append-only. Each occurrence, reopen, fix and validation event should record:
`event`, `regressionKey`, `observedAtKst`, `sourceSha`, build/profile/session identity when available, symptom fingerprint, evidence, root cause, fix SHA, affected paths, verifier, validation result, status and exact nextAction.

This gate is enforced structurally by `tools/Test-VRRegressionKnowledge.ps1` in coordination and active DX9Ex CI. It cannot prove HMD correctness, but it prevents solved regressions from disappearing from project memory.


## Unified production write logging

The production-write contract is origin-independent. Scheduled D, direct Chat edits, and deliberate manual production edits all use the same durable logging path.

### Ledgers

- Issue #14: `[VR] Production Change Ledger` — append-only record of every coherent production change.
- Issue #13: `[VR] Runtime Problem / Regression Ledger` — append-only problem/reopen/fix/validation events.
- `docs/VR_REGRESSION_KNOWLEDGE.json` — machine-readable regression source of truth.

### Source modes

Every production event declares one source mode:
- `SCHEDULED_D`
- `CHAT_DIRECT`
- `MANUAL`

A direct Chat edit is therefore not an informal exception. For the duration of that transaction it follows the same D ownership, checkpoint, validation and regression rules.

### C4.5 LOG — mandatory after production commit

After C4 COMMIT and before C6 STATE, append an Issue #14 event containing:
- sourceMode
- changedAtKst
- baseSha
- resultSha
- changeSummary
- changedPaths
- reason
- relatedFindingOrRegressionKeys
- validation
- runtimeTestRequired
- exact nextAction

When runtime behavior is implicated, also append/update Issue #13 and the regression registry. A known symptom must reuse its existing stable key.

If ledger persistence fails, the run is not fully persisted. Record `PUSH_PENDING` or `CAPABILITY_BLOCKED` and carry that exact action into C6.


## Canonical original-EXE reverse-engineering gate

Executable-RVA reasoning uses one canonical binary baseline:

- upstream: `emoose/OutRun2006Tweaks`;
- asset: release `v0.1/OR2006C2C.EXE`, the same replacement EXE URI used by upstream's own build workflow;
- manifest: `docs/VR_BINARY_CONTRACT.json`;
- verifier: `tools/verify_vr_binary_contract.py`;
- crash signature registry: `docs/VR_CRASH_SIGNATURES.json`.

The EXE itself is not committed. CI downloads it transiently and strict-verifies
its pinned SHA-256, PE32/x86 identity, image base, reviewed RVA byte signatures,
and source bindings.

A/B/C must consult this contract/disassembly whenever a finding depends on game
control flow, HUD/render ownership, call timing, calling convention, register/
stack assumptions, or an executable RVA. Source-only reasoning is insufficient
for a new executable hook.

D integration rules:
1. any new/changed executable-RVA hook must add or update a stable binary
   contract entry;
2. strict canonical-EXE verification must pass before build validation is
   considered sufficient;
3. a candidate touching an RVA/risk path that matches a known crash signature
   must revalidate that stable crash key;
4. discovery mode may be used only to collect evidence for a deliberately
   changed canonical baseline and never counts as an integration pass.

Crash bundles preserve a machine-readable `crash_signature.json` containing
exception code, absolute address, main-module base, thread ID and ASLR-stable
`exeRva` when the fault belongs to the main EXE. This allows direct joining to
the binary contract and durable crash registry.
