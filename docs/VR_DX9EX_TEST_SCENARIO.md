# DX9Ex Focus Test Matrix

This branch intentionally stops multi-backend development until the D3D9Ex path is correct and smooth. DXVK, multiview and DX12 are not built or packaged.

All four candidates use the same runtime policy:

- D3D9Ex promotion enabled
- DirectGPU transport preferred, but Desktop Duplication/SBS fallback allowed if shared-eye transport is not ready
- OpenXR cadence PhaseLock enabled with target 0 = runtime-selected refresh rate
- 60 Hz simulation retained while rendering may follow 72/80/90/120 Hz
- framerate interpolation enabled
- SkyGlowFactor = 1
- no DXVK d3d9.dll
- no multiview patcher
- no DX12 host

## Test order

### P1_C1_FAST_WORLD
R29 fast LEFT+RIGHT path plus the restored R27/R28 perspective-world classifier. R30-R34 are absent.

Purpose: first test whether road, cars, scenery, particles/billboards and overall stereo geometry return while removing the expensive R26 steady-state mono safety replay.

### P2_C2_FAST_HUD
P1 plus R30 asymmetric-FOV HUD/XYZRHW/SkyGlow corrections. R31-R34 remain absent.

Purpose: if P1 world geometry is good, check whether HUD, white text/rank, smoke/skid and screen-space effects are corrected without reintroducing the full later overlay chain.

### P3_FULL_R34
Current complete R29 -> R30 -> R31 -> R32 -> R33 -> R34 chain.

Purpose: determine whether the later StateBlock/reset/raster safety overlays are required for correctness or whether one of them reintroduces the regression.

### P4_R26_HUD_SAFE
Conservative R26 world path plus the R30 HUD/XYZRHW/SkyGlow overlay.

Purpose: fallback comparison. It keeps the old world authority but restores the HUD/effect overlay. It may be slower; use it mainly if P1/P2 still corrupt world geometry.

## What to check

Use the same short mission or OutRun section. Check road/scenery, player and opponent cars, driver, shadows, sky/clouds, smoke/skid, lens flare, floating opponent rank, white score/rank text, 6th/6, HUD/menu/Yes-No alignment, stereo depth, head tracking and headset smoothness.

Run RUN_DX9EX_TEST.cmd. When the game exits it creates DX9EX_LOGS/DX9EX_LOG_<variant>_<time>.zip. Upload that ZIP with the visual result.

Do not copy files from different variants together. Extract one candidate over the game folder, test it, then extract the next candidate over the same folder.
