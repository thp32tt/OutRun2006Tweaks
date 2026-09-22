# VR Run State

## Role-C v2 handoff — 2026-09-22 21:35 KST

CANONICAL_ROLE:
- Pipeline v2 active: C is implementation + self-recovery worker on isolated `vr-d3d9ex-candidate/<finding>-<run>` branches only; D independently reviews/integrates/packages.
- Integration base recovered: `4ff3a3f98a000e0e19f4ba065066d5f81e9d5417` (`vr-d3d9ex-focus`).
- Never write master/vr-openxr/wheel-ffb or integration from C.

RECOVERY / REGRESSION:
- Loaded `docs/VR_REGRESSION_KNOWLEDGE.json`, `docs/VR_PROBLEM_HISTORY.md`, Issue #6 READY_FOR_C intake, and Issue #14 production-change policy.
- Stable runtime regression `VR-STARTUP-WHITE-001` remains `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`; host `vrhost/**` is a riskPath, so any eventual host candidate must retain its static/build gate and cannot be final DONE without Quest3/VDXR runtime evidence.

SELECTED:
- finding: `VR-OPENXR-BOUNDED-WAIT-RETRY-STALL-001`
- status: `BLOCKED_SAFE_PATCH_MATERIALIZATION`
- base_sha: `4ff3a3f98a000e0e19f4ba065066d5f81e9d5417`
- candidate branch: `vr-d3d9ex-candidate/VR-OPENXR-BOUNDED-WAIT-RETRY-STALL-001-C-20260922T2135KST`
- candidate_sha: none; branch verified identical to base after recovery.
- rootCause: bounded wait converts an infinite wait to a finite failure, while `sbs_capture_override.hpp::Acquire` preserves `acquired=true, waited=false`; repeated projection attempts can therefore repeatedly spend the wait budget on the same acquired image with no bounded escalation/recovery state.
- active-path evidence: `Swapchain` stores acquired/waited/acquiredImage; `Acquire` reuses the oldest acquired image, waits with `XR_INFINITE_DURATION`, and on failed wait returns false without release. `bounded_swapchain_wait.hpp` converts total 250ms timeout exhaustion to `XR_ERROR_RUNTIME_FAILURE`.
- RED oracle intent: fake OpenXR wait must exhaust budget repeatedly on same acquired image, prove no release-before-success, cap consecutive retry epochs, enter defined recovery/escalation state, and prove transient timeout then success recovers normally.
- intended GREEN: add bounded consecutive failed-wait recovery state without violating acquire/wait/release ordering; coordinate with DirectGPU projection and destroy/reset ownership rather than introducing a competing release policy.
- TEST_LEVEL: LEVEL0 deterministic fake swapchain state machine; LEVEL2 only if runtime starvation is observed.
- regression key: `VR-STARTUP-WHITE-001` riskPath trigger because target is under `vrhost/**`; final runtime-visible DONE remains USER_RUNTIME_REQUIRED.

SELF_RECOVERY_EVENT:
- During attempted candidate construction an unsafe whole-file replacement was started because connector output for the large source was truncated. The candidate branch was immediately force-reset to exact base before handoff.
- Verification: compare base vs candidate branch is `identical`, ahead 0 / behind 0 / files []. No production or integration branch was touched and no malformed candidate remains reachable from the candidate branch.
- Classification: capability/safe-materialization block, not product failure. SAFE PATCH forbids reconstructing the full immutable production source from excerpts/chunks.
- CI: not triggered because there is no valid candidate commit.

NEXT_ACTION:
- C must first obtain a complete immutable blob/materialization for `vrhost/src/runtime/sbs_capture_override.hpp` (and inspect DirectGPU interaction) without excerpt reconstruction. Then create a fresh candidate from current integration HEAD, establish deterministic RED, apply minimal GREEN, rerun oracle, trigger authorized candidate CI immediately, and hand exact SHA/run to D.
- Do not reuse commit `6439bb2bd162ecf643dac55303495f42eb9d3328`; it was removed from the candidate branch by recovery reset and must never be integrated.
