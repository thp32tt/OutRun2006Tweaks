# OutRun VR — DXVK R71 disassembly-first branch

Baseline: `vr-r70-structure-squash` at
`b6c208bbc9a411b9c035be26f9e1e9c014028738`.

Development branch: `vr-dxvk-r71-disasm`.

## Goal

Run the proven R70 OutRun render semantics through DXVK without carrying the stale
pre-R70 PoC renderer forward wholesale. Graphics correctness is the first gate;
multiview is a later optimization.

## Why the old PoC is not the base

`vr-dxvk-poc` contains useful DXVK interop/multiview experiments but diverged long
before the current R64-R70 HUD, projected-rank, option-arrow, goal-time, flare and
structure work. It is reference material only.

The new branch therefore starts at R70 and selectively reuses concepts after they are
reconciled with `src/vr/game/disasm_render_contract.hpp`.

## R71 bootstrap

- shared EXE/disassembly render contract;
- passive D3D9 provider census;
- optional stock-DXVK interop detection;
- D3D9Ex exposure detection;
- no custom fork interface;
- no multiview shader patching;
- no draw interception changes;
- no DX12 code.

This phase intentionally cannot change rendered pixels.

## Planned stages

1. R71: compile/passive provider census on the R70 renderer.
2. R72: record the actual DXVK D3D9 state/resource/format surface used by OutRun.
3. R73: stock DXVK two-pass parity with the R70 graphics-correctness gate.
4. R74: lifecycle/Reset/menu/recenter hardening under DXVK.
5. R75: only after parity, recover the old multiview work as a separately gated opt-in path.
6. R76: prove programmable-world c64-c67 multiview while SCREEN_HUD and WORLD_BILLBOARD
   semantics remain exact.
7. R77: performance/frame-pacing comparison and final runtime validation.
8. Promote only after repeated Quest 3/OpenXR validation.

## Disassembly rules

- programmable world stereo is anchored at VS c64-c67, never guessed from primitive count;
- SCREEN_HUD producers are kept separate from WORLD_BILLBOARD producers;
- rival rank markers retain the Calc3D2D/world attachment chain;
- SpriteNode queue entry 0x2D734 remains non-hookable; use the known safe node/epilogue
  boundaries and existing semantic hooks;
- unknown provenance fails closed to the R70 reference path.

## Merge rule

Do not merge this branch into the production/reference line until
`docs/VR_DX11_DXVK_BRANCH_POLICY.md` is fully satisfied by one exact runtime build.

## DXVK version baseline

Development targets stock DXVK 3.1.1 first. On 2026-09-28, v3.1.1 is the latest
official DXVK release. The R71 passive probe retains the stock
`ID3D9VkInteropDevice` IID already validated against the upstream D3D9 interface.

Do not bind the graphics-correctness path to the old custom fork before stock DXVK 3.1.1 parity is demonstrated.

## One-click package path

The DXVK branch PC FAST packager acquires the pinned official DXVK 3.1.1 x86 release when no explicit provider path is supplied. It verifies that `x32/d3d9.dll` is PE32/x86, records SHA-256 provenance, and packages it only under `backends/dxvk`. The package root must remain free of a preselected `d3d9.dll`; `START_HERE_VR_TEST.cmd` activates the backend atomically through the selector.

At R71 the package intentionally contains no `multiviewpatcher.dll`. One-click therefore exercises stock DXVK SAFE/two-pass parity first; multiview remains blocked by the graphics-correctness gate.
