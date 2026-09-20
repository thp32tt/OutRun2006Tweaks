# VR Run State

Updated: 2026-09-20 23:10 KST

## Current checkpoint
- C0 RECOVER: complete — analyzed user logs from matrix `VRM-20260920-803144005c0e`
- C1 REVIEW: complete — delivered D3D9 SAFE path was an R26/R23 regression-isolation build, not the intended completed DX9Ex renderer
- C2 IMPLEMENT: complete — created `vr-d3d9ex-focus`, removed DXVK/DX12 from its dedicated workflow, added four DX9Ex-only comparison candidates and automatic per-variant log collection
- C3 VALIDATE: in progress — DX9Ex-only workflow run `35515548121`
- C4 COMMIT: complete for workflow/test-harness changes
- C5 PACKAGE: pending successful P1-P4 builds
- C6 STATE: current document

## Strategy change
DX9Ex is now the only active renderer target. DXVK, multiview and DX12 are frozen until the user accepts a correct and smooth DX9Ex reference. The generic Build workflow is disabled on `vr-d3d9ex-focus`; only the dedicated DX9Ex four-variant matrix should compile runtime candidates.

## Why the previous package regressed
The last D3D9 SAFE build explicitly compiled the R26/R23/R22/R13/R9 chain and excluded R29-R34 plus renderer R29. Runtime did reach TRUE STEREO SBS compose, so the new corruption was not a simple stereo-transport failure. In heavy gameplay samples the log rose to roughly 1,800-2,000 draws per Present and more than 568k semantic rejects, matching the expensive conservative replay path. The recovery launcher also forced 60 FPS, interpolation OFF and cadence OFF while the OpenXR host reported 90 Hz, adding a separate source of visible judder.

## DX9Ex four-build set
1. `P1_C1_FAST_WORLD`: R29 fast L+R + restored R27/R28 perspective-world classifier.
2. `P2_C2_FAST_HUD`: P1 + R30 HUD/XYZRHW/SkyGlow.
3. `P3_FULL_R34`: full R29-R34 chain.
4. `P4_R26_HUD_SAFE`: R26 world + R30 HUD/effect overlay, conservative comparison.

All use `PreferD3D9Ex=true`, allow fallback when DirectGPU sharing is not ready, enable dynamic OpenXR PhaseLock, remove the forced 60-FPS test cap after XR cadence becomes active, enable interpolation, and keep `SkyGlowFactor=1`.

## Next runtime test
Test P1 -> P2 -> P3 in that order. Use P4 only if the fast-path candidates remain badly corrupted or as a conservative comparison. Use the same short gameplay segment each time and upload the automatically generated `DX9EX_LOG_<variant>_<time>.zip`.
