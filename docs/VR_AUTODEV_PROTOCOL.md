# OutRun2 VR Four-Role Autonomous Development Protocol

This repository-side protocol matches the four Work scheduled roles. The schedule is external; this file defines durable coordination and ownership.

## Integration target and backend scope

- Integration/production branch: `vr-d3d9ex-focus`.
- Stable `master`, `vr-openxr`, and `wheel-ffb` are never autonomous write targets.
- Reference renderer: native Win32 D3D9/D3D9Ex game + x64 D3D11 OpenXR host.
- DXVK, multiview and DX12/D3D9On12 remain paused until the DX9Ex reference milestone is user-accepted or explicit backend-specific evidence requires work.

## Four-role ownership

### A — REVIEW
- Primary role branch: `vr-d3d9ex-review`.
- Production runtime source is read-only.
- Produces evidence, findings, coverage and optional non-production verifier prototypes.
- Persists each run as `docs/automation/runs/A/<run-id>.json` on the review branch.
- Does not rewrite integration state/queue/history.

### B — FIX
- Works only on isolated candidate branches named `vr-d3d9ex-candidate/<finding-id>-<run-id>`.
- Never commits production changes directly to `vr-d3d9ex-focus`.
- One coherent hypothesis per candidate SHA; use runtime/profile flags for hardware-dependent experiments when practical.
- Starts the existing candidate-capable CI immediately after publishing the candidate.
- Persists `docs/automation/runs/B/<run-id>.json` on the candidate branch.
- Two materially different failed fixes for the same unchanged failure => BLOCKED evidence, then move on.

### C — VALIDATION
- Primary role branch: `vr-d3d9ex-support`.
- Does not change production runtime source or merge integration.
- Validates immutable candidate SHA/config/toolchain/profile identity and actual GitHub Actions evidence.
- May add non-production verifier/support tooling on the support branch.
- Persists `docs/automation/runs/C/<run-id>.json`.
- Build success is not HMD correctness; hardware-visible conclusions stay NEED_HMD_TEST.

### D — INTEGRATION / PLANNER
- Sole autonomous writer of production runtime code and consolidated state on `vr-d3d9ex-focus`.
- Consumes A/B/C run records idempotently.
- Revalidates changed base/dependencies before integrating a candidate.
- Owns `docs/VR_WORK_QUEUE.json`, `docs/VR_AUTODEV_STATE.json`, `docs/VR_RUNTIME_FEEDBACK.json`, and `docs/VR_SCHEDULED_RUN_HISTORY.md`.
- Only D freezes/finalizes user test packages.

## Resumable checkpoint model

C0 RECOVER -> C1 REVIEW -> C2 IMPLEMENT if role allows -> C3 VALIDATE -> C4 COMMIT if role allows -> C5 PACKAGE if warranted -> C6 STATE

Every run starts from durable GitHub state and exact SHA/config identity. Completed checks with unchanged relevant input hashes are reused.

## Queue states

Allowed central states:
- READY
- IN_PROGRESS
- NEEDS_VALIDATION
- VALIDATED
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
- candidateSha (B, when created)
- actual CI run/artifact identifiers
- evidence level
- queue proposal
- blockers/retry count
- exact nextAction

D appends one consolidated history entry per consumed run and records the run ID to prevent duplicate import.
