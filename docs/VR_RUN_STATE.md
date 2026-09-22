# VR Run State

## Role-C exact-SHA handoff — 2026-09-22 13:41 KST

REGRESSION_KNOWLEDGE:
- integration_sha: `d961afe38d6417961d65d7e23d3a65f33bcec39c`
- loaded: `docs/VR_REGRESSION_KNOWLEDGE.json`, `docs/VR_PROBLEM_HISTORY.md`, Issue #13, `docs/VR_SUPERPOWERS_POLICY.md`.
- active case: `VR-STARTUP-WHITE-001` / `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`.
- stored root cause: synchronous CreateDevice-thread stereo installation previously allocated/mutated private RT/depth before fresh-device initialization completed.
- current candidate intersects explicit riskPaths `src/hooks_graphics.cpp` and `.github/workflows/vr-dx9ex-active.yml`; preserve stable key as EVIDENCE_AUGMENT.
- runtime-visible final DONE still requires USER RUNTIME VERIFIED Quest3/VDXR logo -> menu/game and gameplay stereo-open evidence.

POST_FIX_REVIEW:
- candidate_sha: `c4dd697e2b1f33d3b8af6ab254f378a1cc421248`
- base_sha: `d961afe38d6417961d65d7e23d3a65f33bcec39c`
- finding_ids: `VR-NEARPLANE-ACTIVE-GATE-001`
- regression_case_keys: `VR-STARTUP-WHITE-001` / EVIDENCE_AUGMENT.
- topology: exact merge-base is base SHA; candidate ahead 3 / behind 0.
- changed production file/function: `src/hooks_graphics.cpp` / `FixZBufferPrecision` near-plane eligibility; support changes add `tools/verify_vr_nearplane_active_gate.py` and wire it into `.github/workflows/vr-dx9ex-active.yml`.
- intended source hunk: replace broad `VREnabled && VRPositionalTracking` near-plane activation with `VRPositionalTracking && VRStereo && RuntimeEligibility::MayInjectStereo()` while retaining configured `VRNearPlane` behavior for eligible stereo.
- unintended_diff: PASS; no evidence of stale-base/diverged carryover or unrelated production-runtime hunks.
- active_call_path evidence: production near-plane decision is in `FixZBufferPrecision`; deterministic oracle checks the active-stereo eligibility contract and legacy broad gate removal.
- config/profile impact: no requested change to `SkyGlowFactor=1`, `TargetRefreshRateHz=0`, profile selection or package defaults.
- dependency/regression risk: `src/hooks_graphics.cpp` is a `VR-STARTUP-WHITE-001` riskPath. Candidate narrows render-time eligibility rather than changing the stored deferred CreateDevice/first-Present root-cause protection. Keep startup-white runtime gate open.
- deterministic checks: exact candidate DX9Ex Active Validation run `35684438108` completed SUCCESS. Policy job explicitly ran `Verify near-plane active stereo eligibility` SUCCESS; canonical binary contract and reconstructed architecture checks also succeeded.
- build/CI evidence: run `35684438108`, exact head SHA `c4dd697e...`, all 4 jobs SUCCESS: policy, Win32 active DX9Ex game DLL, x64 D3D11 OpenXR host + deterministic no-HMD smoke, profile-aware package + package validation.
- A review: exact-candidate identity-only A PASS recorded; production source unchanged from previously A-reviewed `b8bd82c3...`.
- B review: exact `c4dd697e...` PASS_DOMAIN_REVIEW_NEED_HMD_GATE with fresh oracle/build evidence.
- C verdict: PASS_EXACT_SHA_BUILD_VERIFIED_NEED_HMD_TEST.
- required final validation: D must perform fresh prospective-merged-tree identity/regression validation if integration HEAD moves; runtime final DONE remains gated on Quest3/VDXR evidence.
- exact nextAction: D may integrate this exact candidate only after confirming integration HEAD still equals `d961afe...` (or recreating/revalidating on moved HEAD), preserving triggered `VR-STARTUP-WHITE-001` evidence recipe and production-change history requirements.

FINDING_ORGANIZATION:
- `VR-NEARPLANE-ACTIVE-GATE-001`: PASS exact SHA / BUILD VERIFIED / NEED_HMD_TEST; READY_FOR_D_INTEGRATION_GATE.
- `VR-STARTUP-WHITE-001`: EVIDENCE_AUGMENT; do not create a new regression key; remains BUILD_VERIFIED_NEED_HMD_TEST.
- `VR-SKYGLOW-ACTIVE-GATE-001`: READY; independent next production source item after near-plane integration gate.
- `CRASH-ZIP-FINALIZE-DURABILITY-001`: READY/VALIDATION_PREP; retain behind SkyGlow unless new failure evidence raises severity.

D_IMPLEMENT_NEXT:
1. `VR-NEARPLANE-ACTIVE-GATE-001` | regression key `VR-STARTUP-WHITE-001` | READY_FOR_INTEGRATION_GATE | target `src/hooks_graphics.cpp::FixZBufferPrecision` | bounded hypothesis: broad near-plane activation can apply VR projection depth behavior when stereo injection is not currently eligible | GREEN fix already present in exact candidate `c4dd697e...` | RED/GREEN oracle `tools/verify_vr_nearplane_active_gate.py`, GREEN in run `35684438108` | dependency/blocker: prospective merged-tree identity and durable production/regression history; final runtime HMD evidence remains open | reviews A+B+C satisfied for exact identity/source risk | priority P0.
2. `VR-SKYGLOW-ACTIVE-GATE-001` | regression key `VR-STARTUP-WHITE-001` if implementation intersects stereo/shared-frame eligibility | READY | target current stereo renderer SkyGlow ownership/active gate | bounded hypothesis: SkyGlow path can remain active from requested stereo state after runtime injection becomes ineligible, causing visual ownership/state work outside active stereo | intended RED oracle: active/inactive eligibility cases preserving `SkyGlowFactor=1` | minimal fix: gate SkyGlow ownership/composite on actual runtime stereo eligibility without changing factor semantics | dependency: current renderer path | review B+C, A if lifetime/ownership changes | priority P1.
3. `CRASH-ZIP-FINALIZE-DURABILITY-001` | no new regression key unless runtime path evidence intersects registry | READY_VALIDATION_PREP | target crash ZIP finalization durability path | bounded hypothesis: interrupted/partial finalization can leave diagnostic artifact identity incomplete or non-atomic | RED oracle: deterministic interrupted/finalize durability check on exact current base | dependency: confirm current-base identity before implementation | review C plus A only if lifecycle ownership changes | priority P2.

VALIDATION_PREP:
- Near-plane candidate: use exact candidate SHA, CI run 35684438108, policy oracle, Win32 game/x64 host/no-HMD/package evidence; re-run/confirm prospective merged tree if integration HEAD moved.
- Triggered regression recipe: build active DX9Ex game DLL + x64 host; deterministic host smoke; preserve deferred stereo resource initialization outside CreateDevice pre-exposure path; runtime CORRECTNESS logo -> menu/game -> gameplay stereo-open before final DONE.
- Package/profile/session identity must remain attributable to exact source SHA/config/profile for human runtime evidence.

READY_for_D: 3
candidates_reviewed: 1
PASS: 1
NEEDS_CHANGES: 0
BLOCKED: 0
findings_organized: 4
regression_cases_triggered: 1 (`VR-STARTUP-WHITE-001`)
exact nextAction: D should consume `c4dd697e...` as the first integration-gate item, verify prospective merged-tree identity/regression evidence, then integrate only if unchanged/fresh gates pass. Next independent source implementation is `VR-SKYGLOW-ACTIVE-GATE-001` with RED -> GREEN oracle first.


## Role-C capability/write-discovery rule — 2026-09-22 15:56 KST

- Before declaring CAPABILITY_BLOCKED for review-state persistence, C MUST discover the connected GitHub actions for `fetch_file`, `update_file`, `create_file`, `create_commit`, and `update_ref` as applicable.
- Existing review/support files MUST be read first to obtain the current blob SHA, then updated sequentially with `update_file`; never run concurrent writes to the same path.
- After each write, C MUST fetch the exact file from `vr-d3d9ex-review-c` and verify the resulting content/identity before claiming persistence success.
- CAPABILITY_BLOCKED is valid only after action discovery or an actual permission/API failure. A tool not being initially visible is not sufficient evidence.
- C persistence is restricted to review/support state on `vr-d3d9ex-review-c`. C MUST NOT write production runtime source, create production candidates, package production builds, or update/integrate `vr-d3d9ex-focus`.
- If `docs/VR_SUPERPOWERS_POLICY.md` is unavailable on the review branch, C records that policy-read limitation but continues only with already-canonical review/support constraints; it must not infer production authority.

## Role-C stale handoff correction — 2026-09-22 15:56 KST

- Previous handoff entry that treated `c4dd697e2b1f33d3b8af6ab254f378a1cc421248` as awaiting D integration is stale once integration branch HEAD equals that SHA.
- `VR-NEARPLANE-ACTIVE-GATE-001`: classify as INTEGRATED / BUILD_VERIFIED / NEED_HMD_TEST; remove from READY_FOR_D integration work. Runtime-visible DONE remains gated by Quest3/VDXR evidence.
- `VR-STARTUP-WHITE-001`: retain stable regression key and USER_RUNTIME_REQUIRED gate.
- D_IMPLEMENT_NEXT after stale-item removal: P1 `VR-SKYGLOW-ACTIVE-GATE-001`; P2 `CRASH-ZIP-FINALIZE-DURABILITY-001` unless newer evidence changes ordering.
- This correction is review/support state only and makes no production write.
