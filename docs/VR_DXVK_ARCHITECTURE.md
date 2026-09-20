# Experimental DXVK VR architecture

Status: active PoC. Production VR remains on `vr-openxr`.

Baseline: `vr-dxvk-poc` was created from the current `vr-openxr` branch on 2026-09-20.

## Goal

Develop DXVK as an independent renderer backend while preserving the proven OutRun-specific
camera, WVP, draw-classification, state-restore, pose-latching and fail-closed logic.

User-facing renderer policy remains:

```text
VRRenderBackend = Auto | D3D9TwoPass | DXVK | DX12
```

Renderer selection and frame transport remain separate decisions.

## Current multiview architecture

The branch no longer uses the earlier capability-zero placeholder provider. It now builds
`Detegr/dxvk-openRBRVR`, which already contains a working D3D9-to-Vulkan multiview
implementation and the public `IDirect3DVR9` extension used by openRBRVR.

Gameplay is rendered into one persistent two-layer D3D9/DXVK color target and, when present,
one persistent two-layer depth/stencil target:

```text
verified OutRun D3D9 draw stream
        |
        +-- programmable verified world draw
        |      |
        |      +-- clone original vertex shader
        |      +-- fetch DXVK-generated SPIR-V
        |      +-- patch only c64-c67 accesses
        |      |     view 0 -> left WVP
        |      |     view 1 -> right WVP
        |      +-- Vulkan BuiltIn ViewIndex
        |      +-- ONE game/D3D9 draw -> Vulkan multiview layers 0 + 1
        |
        +-- HUD / fixed-function / unsafe / unsupported draw
               |
               +-- layer 0 validated left-eye draw
               +-- layer 1 validated right-eye draw
                       |
                       v
          persistent 2-layer color/depth
                       |
                Present boundary
                       |
          CopySurfaceLayers once
             |                 |
       conventional L     conventional R
             \_________________/
                     |
              existing VR host/transport
```

This arrangement is intentional. Mixing a separate right-eye surface with multiview world
draws would break ordering and depth continuity whenever a HUD/effect/fixed-function fallback
appears between world draws. Keeping all stereo work in the same layered color/depth images
preserves the original game draw order.

## Sources incorporated

### Detegr/dxvk-openRBRVR

License: zlib/libpng.

Used directly as the x86 D3D9 provider. Relevant existing functionality:

- `Direct3DCreateVR` / `IDirect3DVR9`;
- two-layer render-target/depth creation;
- `CopySurfaceLayers`;
- DXVK SPIR-V access and replacement;
- shader constant-count control;
- Vulkan multiview pipeline/view-mask handling;
- fixed-function multiview support.

OutRun adds a small source patch because upstream exposes
`SetMultiviewSurfaceLayer` but leaves the corresponding
`D3D9Subresource::SetMultiviewSurfaceLayer` implementation as a TODO. The OutRun patch lets
one persistent array surface switch between layer 0, layer 1 and all layers, and invalidates
cached image views when the selection changes.

### Detegr/RBR-spirvpatcher

License: Mozilla Public License 2.0.

Built and shipped as `multiviewpatcher.dll`. OutRun uses
`ChangeSPIRVMultiViewDataAccessLocation` to patch only the verified OutRun WVP registers
c64-c67. Unlike RBR-specific use, OutRun dynamically allocates two four-vector constant blocks
in unused D3D9 vertex-shader constant space and rejects shaders that cannot fit safely below
the c255 limit.

### Other references

OpenXR Toolkit (MIT), vrframework (MIT), OpenComposite (GPL), Wine/vkd3d-proton (LGPL) and
other VR/wrapper implementations are architecture/failure-mode references. Code is imported
only when it materially improves this branch and its license/source is recorded. UEVR is
architecture reference only because its repository is not published under a reusable
open-source license.

## Fail-closed rules

True one-draw multiview is only attempted when all existing OutRun safety checks pass:

- gameplay stereo is active;
- main render target is the verified logical backbuffer;
- no unsafe auxiliary MRT path;
- no active/unknown occlusion-query ownership;
- pose is valid and latched for the frame;
- draw is a positively identified programmable world draw;
- c64-c67 match the verified OutRun WorldView*Projection upload boundary;
- persistent layered color/depth resources are valid;
- the vertex shader can be cloned and patched safely;
- sufficient D3D9 float constant space exists.

If any condition fails, the original shader remains untouched and that draw uses the validated
two-pass route. Fixed-function, HUD/effects, offscreen passes and unknown draws are not forced
through the programmable multiview patcher.

## Frame and state ownership

A deterministic full main clear initializes both layers. Subsequent game attempts to bind the
logical backbuffer/main depth are redirected to layer 0 only while gameplay stereo is active.
Offscreen targets and MRTs retain normal D3D9 semantics.

Provider-authored D3D9 state changes are wrapped in an internal scope so OutRun's own D3D9
hooks do not mistake them for game-authored state changes.

At Present, the layered color image is copied once into the conventional left/right eye
surfaces. Depth remains internal because no display transport needs it. Reset, main-depth
replacement and leaving gameplay invalidate layered resources and shader/provider state.

## Remaining transport work

True geometry multiview removes most duplicated eligible world draws, but the current PoC
still resolves the two Vulkan layers to the conventional OutRun eye surfaces before the
existing host transport consumes them.

The next independent performance stage is direct Vulkan/OpenXR transport. Raw Vulkan handles
from `IDirect3DVR9` are process-local, so a separate x64 host cannot safely consume them
without explicit external-memory/semaphore export or an in-process compatible OpenXR design.
That transport change must not be conflated with geometry multiview correctness.

## Merge contract with DX12

A later merged branch should keep these backend-neutral:

- pose sampling/latching;
- game camera extraction;
- WVP classification;
- draw eligibility;
- HUD/effect policy;
- telemetry;
- refresh/cadence policy;
- input/FFB;
- configuration UI.

DXVK owns Vulkan multiview/shader translation. DX12 owns D3D9On12/native D3D12 transport and
OpenXR D3D12 submission. Production `vr-openxr` remains unchanged until the experimental
backend passes visual and reset/transition validation.
