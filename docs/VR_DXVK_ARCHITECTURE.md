# Experimental DXVK VR architecture

Status: PoC only. Production VR remains on `vr-openxr`.

Baseline: `vr-dxvk-poc` was created from the current `vr-openxr` branch on 2026-09-20.

## Goal

Develop DXVK as an independent renderer backend while keeping the DX12 PoC separate.
The eventual merged project should expose a renderer choice instead of mixing backend-specific
code into one path.

Target user-facing choices:

```text
VRRenderBackend = Auto | D3D9TwoPass | DXVK | DX12
```

Renderer selection and frame transport must remain separate decisions.

## Why the DXVK path is separate

The current D3D9/OpenXR implementation contains a large amount of reverse-engineered game
knowledge: verified WVP constants, draw classification, pose latching, state restoration,
HUD/effect handling, reset generation tracking, and fail-closed fallback. That knowledge is
valuable, but the implementation details of DXVK multiview are different from the DX12 path.

This branch therefore starts from the latest `vr-openxr` code and does not merge the old
`dxvk-multiview-poc` history, which is far behind the current VR branch.

## Verified upstream DXVK integration points

Current upstream DXVK still exposes `ID3D9VkInteropDevice` from the D3D9 device
`QueryInterface` path. It provides access to the Vulkan instance/device/queue and texture
interop helpers.

Current D3D9 draw submission also still funnels through `PrepareDraw` before DXVK emits
Vulkan work. This makes the DXVK D3D9 draw/shader layer the intended insertion point for a
future true multiview implementation.

The OutRun hook should not try to reproduce DXVK's internal pipeline externally.

## Development stages

### Stage 0 - stock DXVK compatibility

Use unmodified 32-bit DXVK and prove:

1. OR2006C2C starts and reaches gameplay.
2. menus, water, sky, shadows, smoke, skid marks and post effects are correct.
3. input, wheel support and FFB behave exactly as the normal branch.
4. Reset/Alt-Tab/game restart are stable.
5. the DXVK interop probe detects `ID3D9VkInteropDevice`.
6. the existing VR code fails closed when a D3D9Ex shared-eye feature is unavailable.

No multiview code is enabled in this stage.

### Stage 1 - backend dispatcher

Introduce a backend policy layer with the shared enum in
`src/vr/core/render_backend.hpp`.

The DXVK branch must initially route all actual stereo rendering to the existing safe path.
The dispatcher only detects capabilities and records telemetry.

### Stage 2 - custom DXVK fork

Create a separate fork of upstream DXVK and add a minimal OutRun-specific stereo control
interface at the D3D9 layer.

State passed from OutRun to the DXVK fork should be limited to renderer state:

- enabled/disabled;
- pose sequence;
- verified shader/draw generation token;
- left WVP;
- right WVP;
- eligibility token.

Simulation, input and FFB state must never cross this boundary.

### Stage 3 - one multiview route

Enable Vulkan multiview only for the simplest verified opaque world draws.

Required invariants:

- one D3D9 game draw enters DXVK;
- one Vulkan multiview draw is emitted;
- view 0 uses the left WVP;
- view 1 uses the right WVP;
- both views use the same latched pose;
- depth/stencil are view-isolated;
- query/game semantics are unchanged.

Everything else falls back to the proven two-pass route.

### Stage 4 - expand eligibility

Promote draw classes individually after visual/state equivalence is proven:

- stable opaque world;
- alpha-tested world;
- selected transparent effects;
- selected billboards/effects.

HUD, menus, offscreen passes, MRT, occlusion-query-active work and unknown routes stay on
fallback until explicitly classified.

### Stage 5 - Vulkan/OpenXR direct transport

Only after multiview is correct should DXVK transport bypass the current D3D9Ex/D3D11 host
bridge. The long-term target is:

```text
OutRun D3D9 semantics
  -> custom DXVK D3D9
  -> Vulkan multiview eye images
  -> OpenXR Vulkan
```

This removes the need to treat SBS or desktop capture as the normal VR transport.

## Shared merge contract with DX12

The later merged branch should keep these common pieces backend-neutral:

- pose sampling/latching;
- game camera extraction;
- WVP classification;
- draw eligibility;
- HUD/effect policy;
- telemetry;
- refresh/cadence policy;
- FFB/input;
- configuration UI.

Only renderer/transport implementation lives behind backend interfaces.

## Immediate branch policy

`vr-dxvk-poc` is experimental and must not change `vr-openxr` production behavior.
DX12 work remains in `vr-dx12-poc`.
No cross-merge should happen until each backend reaches a stable compatibility baseline.
