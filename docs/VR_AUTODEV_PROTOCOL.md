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
