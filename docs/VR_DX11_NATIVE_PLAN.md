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
- Render-target/depth-surface lifetime needs explicit mirrors.
- Lock/Unlock and dynamic-resource update behavior must match D3D9 expectations.

## 2026-09-28 branch decision

- Keep all native DX11 work on `vr-dx11-native-r71` until the shared graphics-correctness gate passes.
- Use `src/vr/game/disasm_render_contract.hpp` as the backend-neutral EXE contract; do not re-infer HUD/world ownership from primitive/state heuristics.
- DX12 is frozen and is no longer a target for this renderer effort.
- Merge only after static/build validation and Quest 3/OpenXR runtime evidence show the menu/HUD/rank-marker/flare/shadow corruption set is closed.
