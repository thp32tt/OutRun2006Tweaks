# OutRun VR Automation — IMPLEMENTATION-FIRST + EVENING-HMD-MATRIX

Effective: 2026-09-24 KST
Repository: thp32tt/OutRun2006Tweaks
Integration branch: vr-d3d9ex-focus
Protected runtime baseline: R51 17ad376bfdf7939f0851c0c629e4fa094a84f28a

Previous active schedule backup:
- docs/automation/schedule-backups/2026-09-24T2216KST_FLOW-20260924-1.md
- backup commit: de1ecca0da88d15cf0ae7d2d05fc0a87e368be46

## Hourly schedule

| Minute | Automation | Role |
|---|---|---|
| :00 | OutRun A R51 Baseline Guard (Chat) | R51 regression guard and risky-matrix review |
| :20 | OutRun B Active VR Fix Review (Chat) | implementation-ready HUD/flare/perf evidence and matrix comparison |
| :35 | OutRun C Exact Candidate Gate (Chat) | exact-SHA candidate/matrix validation and package identity |
| :45 | OutRun D Implementation-First Integrate (Chat) | sole source writer, builds, integration and evening matrix packaging |

All four remain hourly in Asia/Seoul.

## Core rule: integration is serial, HMD experiments are parallel

Production integration WIP remains exactly ONE.

In addition, up to SIX immutable HMD experiment slots may exist for the next user test session. These experiment slots do NOT count as production integration WIP and must not be merged merely because they build.

All experiment slots must be based on the same declared TEST_MATRIX_BASE unless a slot explicitly documents a dependency on another slot. Every slot records full source SHA, binary SHA256, config/profile hash, feature flags, changed paths, hypothesis and expected observable result.

Prefer one binary with runtime feature flags/profiles when that keeps code identity valid. If a hypothesis changes compiled code and cannot be isolated safely by a runtime flag, use separate immutable binaries/branches.

## Evening matrix target

When enough evidence exists, D should prepare up to six high-information tests:

- A CONTROL: reconciled R51-equivalent/current protected behavior
- B HUD: HUD semantic lifetime candidate
- C FLARE: lens-flare exact-producer candidate
- D PERF: dense-scene instrumentation or measured low-risk optimization candidate
- E HUD+FLARE: interaction candidate
- F FULL: best currently compatible HUD+FLARE+PERF combination

Slots are examples, not a requirement to fabricate work. If a lane lacks implementation-ready evidence, replace that slot with a meaningful alternate hypothesis for an active problem or omit it.

Goal: one evening Quest3/VDXR session should validate multiple independent changes and their interactions, rather than consuming one day per change.

## Development lanes

### Phase 0 — R51 reconciliation
Reconcile vr-d3d9ex-focus/current candidates with the R51 runtime contract without force-resetting protected refs or discarding unique concurrent work.

References:
- R51: 17ad376bfdf7939f0851c0c629e4fa094a84f28a
- R51 restoration/gate candidate: 291fe517aece1ad05f5dac4f0ab72e403ab0fb58
- CD20-17: 312ae9374980ee49c89275652565e0af6e7abd39

Keep only necessary runtime protection/build provenance changes. Do not import unrelated PS2/FFB/localization/general reverse-research changes.

Canonical build flags where applicable:
- OUTRUN_VR_SAFE_DRAW_COMPARE=OFF
- OUTRUN_VR_R26_HUD_COMPARE=ON
- OUTRUN_VR_C1_COMPARE=OFF
- OUTRUN_VR_C2_COMPARE=OFF

### HUD lane
Failed HMD candidate 8d21824f9502b3354fae679972a90868a0cce562 is negative evidence and must not be reapplied unchanged.
Fix semantic ownership at the earliest correct producer/lifetime while preserving generic world/SpriteNode 3D behavior.

### Lens flare lane
Use VR-LENSFLARE-EXACT-PRODUCER-001 and the confirmed dedicated transformed 3D alpha-object path:
0x40CBC0 -> 0x40C9A0 -> DrawObjectAlpha_Internal.
Never treat lens flare as generic SCREEN_HUD.

### Dense-scene performance lane
Instrumentation first, then measured optimization.
Track draw amplification, copies/waits, resource churn/cache misses and frame cadence.

## Parallel preparation vs integration

HUD, lens-flare and performance experiment candidates may be prepared and built in parallel during the day when each has bounded evidence and can be isolated from the common TEST_MATRIX_BASE.

Actual integration stays conservative:
1. reconcile/protect R51 contract;
2. integrate only HMD-supported successful changes;
3. preserve exact evidence for each change;
4. validate combined tree before promoting a new USER_RUNTIME_VERIFIED baseline.

A failed experiment must never regress or block unrelated experiment slots.

## Frozen work

Until the above user-visible lanes are substantially resolved, do not spend primary development time on:
- DXVK
- DX12
- multiview
- broad EXE-map expansion
- general dependency/toolchain cleanup
- PS2/FFB runtime work
- localization runtime work
- broad architecture refactors

Existing infrastructure/reverse knowledge may be reused.

## Interrupt policy

Only these may preempt the user-visible matrix work:
- crash
- white-screen/startup failure
- protected R51 runtime regression
- data corruption
- deterministic build break

Other findings are BACKLOG_ONLY.

## Review routing

- HUD/render/visual/performance: B + C
- architecture/reset/resource/synchronization: A + C
- mixed impact: A + B + C

No review-count quota. Review exact SHAs and matrix deltas only.

## Evening package contract

D should freeze one self-contained EVENING_MATRIX package near 19:45 KST when useful candidates exist. If the day's package was not created and the user changes policy after 19:45, the next D run may create one late-evening package once.

The package should provide simple launchers or a selector for each slot and automatically record:
- Slot ID
- Source SHA
- Binary SHA256
- TEST_MATRIX_BASE
- config/profile hash
- feature flags
- SessionID
- timestamps

One final collector should create one ZIP containing all session logs. The user should not have to manually rename logs.

Default maximum: 6 slots. Fewer is preferable when additional slots do not distinguish a real hypothesis.

## Verification states

STATICALLY_VERIFIED, BUILD_VERIFIED, HMD_EXPERIMENT_READY, INTEGRATED_NEEDS_HMD and USER_RUNTIME_VERIFIED remain distinct.

Only matching Quest3/VDXR runtime evidence can promote a visual/runtime change to USER_RUNTIME_VERIFIED.
