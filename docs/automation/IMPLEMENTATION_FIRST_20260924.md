# OutRun VR Automation — IMPLEMENTATION-FIRST-20260924

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
| :00 | OutRun A R51 Baseline Guard (Chat) | R51 architecture/regression guard only |
| :20 | OutRun B Active VR Fix Review (Chat) | current-lane implementation-ready rendering evidence |
| :35 | OutRun C Exact Candidate Gate (Chat) | exact candidate/CI/integration readiness |
| :45 | OutRun D Implementation-First Integrate (Chat) | sole source writer/build/integrate/package |

All four remain hourly in Asia/Seoul with exact scheduling.

## Development policy

Progress is measured by corrected runtime behavior and integrated source, not review count.

Removed:
- 150-unit / CP150 review quotas
- broad discovery while an actionable fix exists
- routine DXVK/DX12/multiview work
- general EXE-map expansion and dependency/tooling cleanup as primary work
- parallel runtime candidates

One active runtime candidate maximum.

## Strict lane order

### Phase 0 — R51 reconciliation
Reconcile vr-d3d9ex-focus/current candidates with the R51 runtime contract without force-resetting protected refs or discarding unique concurrent work.

Existing references are evidence, not mandatory tips:
- R51: 17ad376bfdf7939f0851c0c629e4fa094a84f28a
- R51 restoration/gate candidate: 291fe517aece1ad05f5dac4f0ab72e403ab0fb58
- CD20-17: 312ae9374980ee49c89275652565e0af6e7abd39

Keep only necessary runtime protection/build provenance changes. Do not import unrelated PS2/FFB/localization/general reverse-research changes.

Canonical build flags where applicable:
- OUTRUN_VR_SAFE_DRAW_COMPARE=OFF
- OUTRUN_VR_R26_HUD_COMPARE=ON
- OUTRUN_VR_C1_COMPARE=OFF
- OUTRUN_VR_C2_COMPARE=OFF

### Phase 1 — HUD semantic lifetime
Only HUD is the production feature target.
Failed HMD candidate 8d21824f9502b3354fae679972a90868a0cce562 is negative evidence and must not be reapplied unchanged.
Fix semantic ownership at the earliest correct producer/lifetime while preserving generic world/SpriteNode 3D behavior.

### Phase 2 — Lens flare
Use VR-LENSFLARE-EXACT-PRODUCER-001 and the confirmed dedicated transformed 3D alpha-object path:
0x40CBC0 -> 0x40C9A0 -> DrawObjectAlpha_Internal.
Never treat lens flare as generic SCREEN_HUD.

### Phase 3 — Dense-scene performance
Instrumentation first, then measured optimization.
Track draw amplification, copies/waits, resource churn/cache misses and frame cadence.

## Interrupt policy

Only these may interrupt the ordered lane:
- crash
- white-screen/startup failure
- protected R51 runtime regression
- data corruption
- deterministic build break

All other newly discovered issues are BACKLOG_ONLY until the current ordered lane is completed or explicitly blocked.

## Review routing

- HUD/render/visual/performance: B + C
- architecture/reset/resource/synchronization: A + C
- mixed impact: A + B + C

No review-count quota may delay an exact candidate handoff.

## User-runtime rule

STATICALLY_VERIFIED, BUILD_VERIFIED, INTEGRATED_NEEDS_HMD and USER_RUNTIME_VERIFIED remain distinct.
Only matching Quest3/VDXR runtime evidence may advance the protected user-runtime baseline.

## Package rule

Default: one DX9Ex CORRECTNESS package.
Up to three only when a concrete A/B comparison is required.
No routine DXVK/DX12 payloads while phases 0–3 are open.
