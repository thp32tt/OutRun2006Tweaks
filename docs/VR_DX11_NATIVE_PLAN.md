# OutRun VR — Native D3D11 backend

Baseline: `vr-r70-structure-squash` at `b6c208bbc9a411b9c035be26f9e1e9c014028738`

Development branch: `vr-dx11-native-r71`

## Goal

Keep the game as a D3D9 caller, but translate the D3D9 behavior actually used by
OutRun 2006 into a native D3D11 renderer and eventually submit directly to the
OpenXR D3D11 swapchain.

```text
OutRun2006C2C.exe
  -> intercepted D3D9 API
  -> OutRun-specific state/resource/draw translation
  -> native D3D11 renderer
  -> OpenXR D3D11 swapchain
```

## Non-regression rule

R69/R70 DX9Ex stays the reference/fallback backend until D3D11-native passes
visual, HUD, lifecycle and frame-time validation. R71 does not install DX11
hooks or alter DX9Ex Reset/StateBlock, transport, HUD semantics or host behavior.

## R71 bootstrap

- D3D11 hardware device/context creation with BGRA support.
- Color Texture2D + RTV + SRV ownership.
- Resize and begin-frame viewport/clear.
- Initial D3D9 -> D3D11 translations for blend, blend-op, depth comparison,
  culling and primitive topology.
- Exact/inexact translation result so unsupported behavior is never silently
  accepted as production-correct.
- Win32 DLL links D3D11/DXGI, but the backend remains dormant.

## Planned stages

1. R71 backend bootstrap.
2. R72 runtime census of actual D3D9 states/FVF/declarations/formats/shaders/primitives.
3. R73 VB/IB/texture/surface mirrors and lifetime tables.
4. R74 cached D3D11 pipeline states and fixed-function shader generation.
5. R75 mono DrawPrimitive/DrawIndexedPrimitive translation.
6. R76 DX9Ex vs DX11 visual parity.
7. R77 stereo + proven HUD/marker/projected-effect semantics.
8. R78 direct OpenXR D3D11 graphics binding, removing shared transport in this mode.
9. R79 lifecycle/recenter/menu/frame-pacing hardening.
10. Promote only after repeated HMD validation.

## Known gaps

- D3DPT_TRIANGLEFAN needs triangle-list expansion.
- D3DBLEND_BOTHSRCALPHA/BOTHINVSRCALPHA need pair-aware conversion.
- Fixed-function texture stages need generated/cached shaders.
- FVF/vertex declarations need D3D11 input-layout generation.
- Render-target/depth-surface mirrors now have one dormant generation-bound owner for exact non-MSAA DEFAULT surfaces; live D3D9 surface registration/binding and proven D3D9-to-DXGI MSAA quality mapping remain pending.
- Lock/Unlock and dynamic-resource update behavior must match D3D9 expectations.

## 2026-09-28 branch decision

- Keep all native DX11 work on `vr-dx11-native-r71` until the shared graphics-correctness gate passes.
- Use `src/vr/game/disasm_render_contract.hpp` as the backend-neutral EXE contract; do not re-infer HUD/world ownership from primitive/state heuristics.
- DX12 is frozen and is no longer a target for this renderer effort.
- Merge only after static/build validation and Quest 3/OpenXR runtime evidence show the menu/HUD/rank-marker/flare/shadow corruption set is closed.

## R72 passive census foundation

R72 now reuses the validated D3D9 stereo hook chain instead of installing a second
render-state/draw hook stack.

- `device_probe.cpp` records the live OutRun backbuffer size/format/MSAA and reports
  whether the dormant R71 native target can represent it.
- `vr/core/d3d9_draw_state.hpp` exposes a backend-neutral snapshot backed by the existing
  periodically revalidated D3D9 render-state shadow.
- `pipeline_translation.cpp` converts the captured subset into D3D11 blend/depth/raster
  descriptors with an explicit unsupported bitmask.
- `runtime_census.cpp` samples one of every 64 game-authored draws when
  `OUTRUN_VR_DX11_CENSUS=1`, counting exact vs unsupported pipeline states and
  fixed-function vs programmable draws.
- The DX11 one-click target enables this census automatically and restores the environment
  after the run.
- `NativeDrawPathActive` remains false. No game draw is redirected to D3D11 in R72.

The census output determines the next implementation order; unsupported alpha test,
fixed-function lighting/fog, stencil, separate-alpha blend, sRGB and topology cases are not
silently approximated.

## R72/R73 resource-format exactness

- Startup backbuffer and runtime texture/index format classification now use one conservative `resource_translation` contract.
- Unsupported luminance/palettized/bump/floating or otherwise unproven formats stay inexact and therefore cannot be promoted to the native draw path.
- The passive census reports unsupported index/texture format samples separately from pipeline-state failures.
- This is observation/gating only; `NativeDrawPathActive` remains false until resource lifetime, shader/input translation and runtime visual parity are complete.


## 2026-10-04 Quest 3 / VDXR runtime direction

User HMD A/B evidence changes the implementation priority.

Observed direction:

- The DX9Ex reference still shows perceptible frame-time stalls even when
  `DirectGpuOnly=true`; DirectGPU-only policy is therefore not the primary
  explanation for the smoother DX11 development path.
- The DX11 development package held the OpenXR/Virtual Desktop stream near 90 Hz,
  but the old launcher forced the game renderer to 60 Hz with cadence disabled.
  The resulting approximately 60->90 3:2 fresh/cached pattern explains visible
  micro-judder even while the compositor reports 90 fps.
- The DX11 development launcher must therefore use XR-native phase-lock
  (`FrameCadenceMode=1`, target 0/auto), unlocked/interpolated rendering and
  desktop VSync disabled while keeping the game simulation at 60 Hz.
- Keep `DirectGpuOnly=true` for the primary gameplay transport. Menu/theater
  fallback may still use Desktop Duplication until native menu rendering exists.
- Runtime census evidence showed programmable-shader draws dominate the observed
  game workload. Fixed-function completion remains correctness work, but it is
  no longer the highest-value path to native coverage.

Revised development priority:

1. Stabilize XR-native 72/80/90/120 Hz render cadence and eliminate repeated-frame
   micro-judder. Track fresh/cached projection ratios and frame-time spikes, not
   the Virtual Desktop fps counter alone.
2. Prioritize programmable vertex/pixel shader fingerprint translation, object
   creation, input linkage, constant propagation and cache ownership.
3. Complete D3D9-to-D3D11 MSAA/backbuffer compatibility and resource
   mutation/lifetime exactness required by the dominant programmable path.
4. Close remaining fixed-function/render-state exactness gaps that are actually
   observed by census or visual parity tests.
5. Keep `NativeDrawPathActive=false` until the activation gate has exact
   resource/shader/state coverage and repeated Quest 3/VDXR parity evidence.
6. Treat DX9Ex as the regression/reference and compatibility backend. Do not
   spend primary optimization effort trying to make its current stall profile
   match the DX11 development path unless a DX11 regression requires it.

Promotion evidence must distinguish three layers: OpenXR compositor cadence,
fresh game-render cadence, and 60 Hz simulation cadence. A reported 90 fps alone
is not sufficient evidence of smooth 90 Hz rendering.
