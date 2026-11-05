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

## DX11 rule

R71 remains dormant until explicit activation work. State/resource translation must report
unsupported or inexact D3D9 behavior rather than silently approximating it. Runtime census
comes before replacing the proven D3D9 draw owner.
