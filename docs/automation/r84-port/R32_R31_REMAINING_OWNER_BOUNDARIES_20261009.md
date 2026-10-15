# DX9Ex R84 – R32/R31 remaining compile ownership boundaries

Reviewed 2026-10-09 KST from authenticated `vr-d3d9ex-focus` source. This is a preflight inventory, **not** a claim of an independently compiled R32/R31 TU.

## Completed, exact validated

- R33/R32 separate-TU/API existing result `CONVERSION-DX9EX-00510`.
- `R30SupportBorrowedRightEyeSurface`: validated material `053096b28e4dd1547579cf15b6e6ccf3663bf487`, prior session.
- `R32ReviewTrackedRenderTarget` and `R32ReviewTrackedDepthStencil` delegate to new borrowed R30 APIs at material `11b71a236af4b0112900061d7130875c4ae6d1e1`; DX9Ex Active `37889666629` and Domain `37889666717` both SUCCESS.

## Still directly coupled in R32 review facade

| Dependency class | Live source example | Smallest next bounded seam |
|---|---|---|
| Right-eye depth and resource setup | `R32ReviewRightEyeDepth` still reads `RightEyeDepth`; `R32ReviewEnsureStereoResources`, `R32ReviewTryBootstrapRightDepth` directly invoke lower implementation | Borrowed depth identity first; then resource ensure/bootstrap only with exact delegation tests |
| R9 depth and stereo fail-close | `R32ReviewMainDepthGeneration`, `R32ReviewMainDepthHasStencil`, depth/stencil sync, `R9Poison` | Group query or failure-reporting owner API separately; retain fail-closed order |
| R22 raster replay | `R32ReviewRunRasterReplayGuardCallback` instantiates `R22RasterReplayGuard` | Encapsulate replay lifetime without moving physical hooks |
| R29 effect/world ownership | `R29StableStereoBase`, `R29FragileEffectCached`, `R29TelemetryNoteStableTwoEyeDraw` | A narrow R30-support snapshot/query boundary; no HUD/effect reclassification |
| D3D hook storage | `SetRenderTargetHook`, `SetDepthStencilSurfaceHook`, four raw Draw hooks and `PresentHook` | One hook-family per extraction, preserve trampoline vs live-call fallback |
| Frame/pose shared state | `FrameStereoPoseSequence`, `FrameStereoMetadata`, `FrameRightDrawFailed`, world/HUD duplicate counters | Extract read/snapshot separately from mutation, enforce frame/pose generation |
| Screen-space owner types | `R30ScreenSpaceKind`, `R30ClassifyScreenSpacePass`, `R30BuildScreenSpaceEyeConstants` | Public semantic adapter, preserve currently protected recentered HUD plane |
| Lower entrypoint targets | `ResetDestR22`, `PresentDestR13`, `ResolveDirectTransportR13`, `SetRenderStateDestR29`, R30 draw destination functions | Owner-provided install target interfaces, no physical hook relocation |

## Previously documented blocking evidence

- `docs/automation/r84-port/R32_R31_SPLIT_PREFLIGHT.json`: 00512 failed split compile on inherited lower runtime/Reset/DirectGPU dependencies.
- `docs/automation/runs/CONVERSION-DX9EX-00513.json`: R31/R30 premature split blocked after three attempts. Do not re-run without a new concrete boundary.
- Historical Windows failed job `112702805352` includes R32 unresolved lower symbols (Settings/VRTelemetry, R29EffectTelemetrySnapshot, SharedState, etc.). Many have since been removed; use the **current** source, not stale diagnostics, to identify remaining blockers.

## Gate and preservation

Do not flip `OUTRUN_VR_REFACTOR_SPLIT_R32_R31` or `OUTRUN_VR_REFACTOR_SPLIT_R31_R30` to production until all required owner declarations, linkage and exact R33 full-chain Win32 compile pass. Keep R26+R30 active HUD, F11 user-reported normal, original GOAL pair, rank/rival DDS, pose, DirectGPU ACK/fence, and RUNTIME_VALIDATION=UNTESTED as independent obligations. No 1000/5000 HUD static repetition.
