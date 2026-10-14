# DX11 live-game frame performance reference — 2026-10-14

Scope: `vr-dx11-native-r71`, original inspection `e9bcef1b5011e22828e83e5c0ad16b145c00ad25`; rebased work from `7b673376b443583f0140bd0b4b51164c01bd3ef9`. The native path is an **opt-in diagnostic** 256x144 inset alongside original D3D9 rendering, not full replacement. Default original D3D9 Draw/Present/input and DX9Ex fallback must remain intact. No FPS gain or Quest3/VDXR parity can be claimed before matching runtime testing.

## Ordered engineering backlog (source-confirmed structural costs, not profiler ranking)

1. **Native VB/IB and Stage1 constant uploads (first implemented candidate):** replace per-Draw `D3D11_USAGE_IMMUTABLE` / `CreateBuffer` calls with lazily growing slot-local `D3D11_USAGE_DYNAMIC` buffers, `Map(WRITE_DISCARD)`, `Unmap`. One slot per admitted batch draw (max 8); indexed and non-indexed draw paths share the same index. Grow only on capacity misses. Discard across frames is safe for in-flight GPU work; Reset releases all GPU buffers. On allocation/Map failure abort diagnostic publication while original D3D9 game Draw/input continues. Use counter instrumentation later to prove allocation reductions.
2. **Shader cold-start:** `ensure_pipeline()` invokes `D3DCompile` for many fixed combinations at first init. Next independent change should move fixed precompiled bytecode to an offline/CI-generated manifest, preserve exact VS/PS entrypoint mapping, bytecode validity, DX11 feature-level behavior, and live DX9Ex fallback. Do not add shader-caching by path alone or silently disable shaders.
3. **Texture mirror lifetime:** `mirror_texture()` copies/decodes D3D9 texels and creates D3D11 texture/SRV per sampled draw, except the existing safe Stage0==Stage1 SRV reuse. Implement only with verified mutation generations, palette changes, mip/sRGB identity, reset/lost-device invalidation, and dynamic/default-pool write hooks. Pointer-only caching risks stale menu/car/race content; avoid until tracked.
4. **Render-target readback:** `GetRenderTargetData()` is a GPU→CPU synchronization/readback followed by GPU upload. Long-term goal is native GPU-owned RT producer→consumer; until then preserve size caps and fail-closed behavior, no blind removal.
5. **State-query and state-object reuse:** count `GetRenderState`, `GetSamplerState`, OM/blend rebindings; extend caches only where source-owned state transitions and reset are known. Existing blend/depth caches are not zero.

## Acceptance gates

- C++ portable capacity/batch probe and Python adversarial integration mutations; exact-SHA Windows compile + DX11 Fast Structural + Backend Conversion + OpenXR + HUD/Build without CI skips. If CI fails, no DONE_BUILD_VERIFIED or score.
- Verify nonindexed `Draw` and indexed `DrawIndexed`, 1/8 contiguous batching, capacity growth, bounded Reset, GPU-lifetime-safe DISCARD, and original D3D9 fallback on any failed allocation/Map.
- On real game + Quest 3/VDXR, capture same menu/car/race scenes before/after: warm/cold first Draw time, p95/p99 CPU/GPU frame time, native CreateBuffer/Texture2D counts, upload bytes, real game FPS, 72Hz/120Hz frame budget, input/HUD/flare parity. 120FPS=8.33ms, 72Hz=13.89ms. Runtime evidence presently **UNTESTED**.

References: Microsoft D3D11 dynamic resources (https://learn.microsoft.com/en-us/windows/win32/direct3d11/how-to--use-dynamic-resources), `ID3D11DeviceContext::Map` (https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-map), and `Flush` (https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-flush). Do not change the per-diagnostic-frame `Flush()` without readback/fence latency tests.
