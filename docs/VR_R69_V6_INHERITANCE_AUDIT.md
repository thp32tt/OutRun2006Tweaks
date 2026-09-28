# R69 V6 inheritance audit

Source checkpoint: `92ce3403c6e68fe5c945b88440e5fa7d5d23cd4d`

## Active runtime graph

### Game / x86
- D3D9 upgraded to D3D9Ex through the R15 compatibility chain.
- Stereo world/effect owner: R26/R23/R22/R13/R9 lineage.
- Production HUD/XYZRHW/SkyGlow overlay: `stereo_renderer_r30_r26_safe.cpp`.
- Renderer/WVP owner in the R26+HUD production configuration: `outrun_renderer_r23.cpp`.
- `outrun_renderer_r29.cpp` and stereo R31-R34 are intentionally excluded in this HMD-proven production configuration.

### Host / x64
- D3D11 OpenXR host.
- R32 DirectGPU fast-submit is the normal path.
- R24/SafeEye and earlier hardening layers remain intentional fallback/recovery layers.

## Confirmed cleanup defect fixed

`stereo_renderer_r30_r26_safe.cpp` still named its lower callbacks and diagnostics as R29 even though it compiles and hooks the R26/R23 chain. This could cause later reviews to assume renderer R29 correctness behavior was inherited when it was not.

V6 renames these callbacks/logs to the actual R26 lower owner and extends `verify_vr_proven_baseline.py` so stale R29-owner labels fail validation.

## Reviewed but not backported in V6

The following R29/R34 behavior is not silently imported because it changes runtime-visible rendering policy and needs an isolated HMD candidate:
- R29 generation-local WVP reconstruction / StateBlock stock-WVP protection.
- R29 conservative fragile alpha/billboard/shadow classification.
- R31-R34 StateBlock/depth-state/final raster overlays.
- R34 duplicate ResetEx health guard.

R15 already publishes ResetEx failure through `RuntimeEligibility::ExternalSafetyBlock`; the R26/R30 production path consumes `MayInjectStereo()`, so ResetEx replay failure remains fail-closed without R34.

## V6 intent

No visual policy change. V6 is a structural-identity cleanup and regression guard on top of the current V5 runtime behavior.
