# R69 CLEAN performance optimization history

Baseline: S10 `b61b81504f9138a2d082e980dc177f877f0b658b`

Goals:
- Preserve R69/S10 visual and safety behavior.
- Improve VR-only performance without changing normal 2D rendering quality.
- Keep each optimization stage independently testable.
- Prefer removing provably dead/redundant work before higher-risk zero-copy changes.

## P1 — VR SkyGlow bandwidth reduction
- Branch: `vr-d3d9ex-candidate/r69-perf-p1`
- Source SHA: `13025145a4e110928e0e97fe4b6a6d9a983e5196`
- Stereo SkyGlow working resolution is fixed to factor 2 while the normal 2D path remains untouched.
- A half-width/half-height buffer uses 25% of the factor-1 pixel count.
- Cached reduced/temp render-target surfaces replace per-frame GetSurfaceLevel/Release traffic.
- Removed SkyGlow blur passes whose output was not consumed by the R69 composite path. This preserves the R69 visual source selection while eliminating dead GPU work.

## P2 — production draw hot-path cleanup
- Branch: `vr-d3d9ex-candidate/r69-perf-p2`
- Source SHA: `72408ba589e0440d8ce7876f1689cb83b9e61497`
- R62 fixed-function diagnostic atomics/logging now run only with VR telemetry enabled.
- R63 exact HUD tracing now exits before atomic/GetFVF/GetVertexShader work when telemetry is disabled.
- Production draw hooks skip the R63 call entirely when telemetry is disabled.

## P3 — SkyGlow invariant-state batching
- Branch: `vr-d3d9ex-candidate/r69-perf-p3`
- Source SHA: `d6a618144fb44ba71b8126b015bd66f92c82ae0e`
- Vertex shader/FVF, sampler and depth/stencil/alpha-test state common to all SkyGlow passes are configured once per SkyGlow frame instead of once per pass.
- Per-pass work is reduced to render target/viewport, shader/source, blend/color-write, constants and draw.
- Full D3D9 state-block restoration is intentionally retained for safety until HMD profiling proves it worth replacing.

## P4 — DirectGPU descriptor hot-path cache
- Branch: `vr-d3d9ex-candidate/r69-perf-p4`
- Source SHA: `83acbf3a38338b483a91891ddd42fd7179eb676f`
- Removed a duplicate per-frame DirectGPU resource-size validation because R23StageDirectHold performs the stricter descriptor validation immediately afterward.
- Source texture descriptors are cached per ring slot, handle pair and transport generation.
- Steady-state DirectGPU frames avoid repeated D3D11 GetDesc calls while retaining width/height/format/sample/mip/array validation on cache fill.

## Deferred until runtime evidence
- Do not remove the host-owned DirectHold CopyResource pair yet; it is part of the current producer-slot lifetime/ACK safety proof.
- Do not remove D3DSBT_ALL restoration yet; replace it only after P1-P4 runtime validation.
- Do not alter the 8 ms legacy SafeEye fence path until logs confirm it is actually being entered during the observed frame drops.
- Do not change stereo world draw ownership or semantic classification as a performance shortcut.
