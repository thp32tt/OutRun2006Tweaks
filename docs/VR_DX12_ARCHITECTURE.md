# Experimental D3D12 VR architecture

Status: PoC only. Production VR remains on `vr-openxr`.

## Goal

Replace the long-term normal rendering path:

```text
D3D9 -> stereo replay/state restore -> D3D9Ex sharing -> D3D11 host -> OpenXR
```

with:

```text
D3D9 semantics -> D3D9On12/D3D12 -> per-eye D3D12 rendering -> OpenXR D3D12
```

without losing the reverse-engineered facts already proven by the current
project.

## Evidence that remains authoritative

The DX12 branch must preserve these invariants:

- OutRun's verified View / Projection / WorldView globals remain the game
  camera source.
- VS c64-c67 remains the verified upload boundary for
  `Transpose(WorldView * Projection)`.
- One immutable render pose is latched for one presented game frame.
- Simulation, input, timers and native FFB run once.
- Only GPU rendering work is duplicated for the second eye.
- The OpenXR pose/FOV submitted for a frame must be the pose/FOV used to render
  that frame.
- Reset, adapter and session generations invalidate stale resources.

## Why D3D9On12 first

D3D9On12 lets the game retain D3D9 API semantics while Windows maps the work to
D3D12. The `IDirect3DDevice9On12` interop interface exposes the underlying
D3D12 device and supports check-out/check-in of D3D9 resources as
`ID3D12Resource` objects.

This avoids starting by writing another full D3D9 implementation. Microsoft
D3D9On12, DXVK D3D9 and d912pxy are reference material for behavior and
performance, but the first executable path uses the Windows system D3D9On12.

## Separation from production

The first DX12 commits live under `dx12poc/` and a dedicated GitHub Actions
workflow. They do not change the production D3D9 stereo hook graph or x64 host.

The production path is the visual/behavior oracle until the DX12 path matches
it.

## Staged architecture

### Stage A: D3D9On12 stock rendering

```text
OR2006C2C.EXE
   -> Direct3DCreate9 interception
   -> Direct3DCreate9On12Ex
   -> stock D3D9 game rendering
   -> D3D12 backend
```

Acceptance: menus, gameplay, sky, shadows, smoke, skid marks and result screens
match stock 2D behavior.

### Stage B: resource interop and telemetry

Track:

- render-target/depth formats;
- D3D9 resource -> D3D12 resource identity;
- shader hashes;
- c64-c67 updates;
- viewport/scissor/state-block activity;
- reset/device generation;
- GPU fence ownership.

No stereo modifications until this trace is stable.

### Stage C: stereo

Create explicit left/right D3D12 render targets and duplicate only rendering
submission at the verified world boundary.

Screen-space/UI/effect passes default to fail-closed/mono until classified.

### Stage D: OpenXR D3D12

The x64 host gains a D3D12 OpenXR binding. Direct per-eye resources become the
normal path, while the existing D3D11 host remains available for A/B validation
during migration.

### Stage E: cleanup

After equivalent behavior is proven:

- remove normal-path D3D9Ex sharing;
- remove SBS/Desktop Duplication from normal gameplay;
- keep only diagnostic/fallback paths that still provide real value;
- add PSO/descriptor/upload caches;
- profile 72 Hz, then 90 Hz, then 120 Hz.

## Non-goals of the first PoC

- shipping a private build of `d3d9on12.dll`;
- rewriting every D3D9 feature;
- replacing the current VR implementation before 2D compatibility is proven;
- changing FFB behavior.
