# OutRun VR DX11 / DXVK branch policy

Baseline: `vr-r70-structure-squash` at `b6c208bbc9a411b9c035be26f9e1e9c014028738`.

Active renderer branches:

- DX11 native: `vr-dx11-native-r71`
- DXVK: `vr-dxvk-r71-disasm`

DX12 development is frozen. Historical DX12 branches remain only as reference evidence;
do not merge, package or extend them unless this policy is explicitly changed.

## Shared renderer contract

Both active branches must consume the same reverse-engineered game semantics instead of
inventing backend-specific render heuristics.

Authoritative anchors are centralized in
`src/vr/game/disasm_render_contract.hpp` and are backed by the existing
`tools/analyze_outrun_exe.py` / HUD inspector pipeline:

- live View / Projection / WorldView globals;
- final programmable-world WVP upload at VS c64-c67;
- canonical SpriteNode queue node/epilogue boundaries;
- Calc3D2D;
- exact rival-rank marker call sites;
- critical SCREEN_HUD versus WORLD_BILLBOARD producer ranges.

The queue entry RVA 0x2D734 is evidence only and must not be used as a mid-hook target.
The existing crash history at the relocated entry/prologue remains binding.

## Isolation rule

No DX11 or DXVK experiment may alter the R70 reference branch. Backend work stays on its
own branch until the visual gate below is complete. Do not merge DX11 into DXVK or DXVK
into DX11 while the gate is open; only shared, reviewed game-semantic contracts may be
reproduced in both branches.

## Graphics-correctness merge gate

A backend is not merge-ready until the same runtime build proves all of the following:

1. logo -> menu -> race -> goal/menu transition completes without white/black stall;
2. road, scenery, vehicles and shadows are coherent in both eyes;
3. menu car models and other 3D menu content are not split/corrupted;
4. lens flare / projected effects do not appear as an incorrect doubled screen-space pair;
5. option arrows, YES/NO and other menu overlays have the intended stereo/head-lock policy;
6. HUD time/rank/goal/name elements are neither doubled nor incorrectly head-following;
7. vehicle 1st/2nd/3rd/... world rank markers remain attached to their source vehicles;
8. Reset/device recreation/recenter does not corrupt render state;
9. unsupported/unknown draws fail closed to the validated reference path;
10. static EXE contract + build CI pass, followed by Quest 3 / OpenXR runtime validation.

Performance work may be measured before this gate closes, but performance alone cannot
promote a backend.

## DXVK import rule

The old `vr-dxvk-poc` branch is reference material, not a merge base. It is hundreds of
commits behind R70 and contains renderer changes that predate the current HUD/flare/rank
semantics. Port individual ideas only after they are reconciled with the R70 contract.

Start with provider/capability detection and stock two-pass parity. Multiview and custom
DXVK-fork interfaces stay opt-in until stock DXVK rendering has passed the graphics gate.


### External interop evidence: GeneralsVR (2026-10-06 review)

GeneralsVR is useful evidence for a later hosted-DXVK experiment, not a reason to bypass the
stock-DXVK gate above. Its current VR host contract documents a driver-tested resource direction:
the x64 host creates D3D11 shared eye textures/fence and the 32-bit game imports those resources
into the DXVK-owned Vulkan device. That project reports the reverse Vulkan-export -> D3D11-open
direction failing with `E_INVALIDARG` on its tested Windows hardware.

For OutRun this becomes a bounded future experiment only:

- keep stock DXVK two-pass rendering and current graphics-correctness gate authoritative;
- do not copy GeneralsVR's game-specific interop code or private DXVK assumptions;
- if a custom DXVK interop lane is later enabled, test host-owned resources first rather than
  assuming Vulkan-export -> D3D11-open will work;
- require adapter-LUID identity, explicit lifetime/fence ownership, exact eye-frame provenance,
  and a fallback that leaves the validated stock provider unchanged;
- compare the experiment with the x64-host timing counters before promoting it for performance.

This is design evidence only. It does not change the current provider or enable a custom DXVK fork.

## DX11 rule

R71 remains dormant until explicit activation work. State/resource translation must report
unsupported or inexact D3D9 behavior rather than silently approximating it. Runtime census
comes before replacing the proven D3D9 draw owner.
