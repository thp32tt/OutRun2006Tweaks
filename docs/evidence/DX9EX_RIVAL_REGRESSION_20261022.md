# DX9Ex rival marker regression root cause — 2026-10-22

## User-observed invariant

The rival marker was visually correct before the recent 1st–5th vehicle-rank repair work and regressed together with the ordinal-rank experiments. Treat rival and ordinal rank as independent optical owners.

## 16.57 GiB capture availability

The 2026-10-22 16.57 GiB `OutRun2006Tweaks.log` evidence bundle does **not** contain a rival observation. The normalized summaries contain no `RIVAL`, `0xBB6F0`, `0xBB6F5`, or `0xBB796` line. Therefore that capture cannot be used as a runtime PASS/FAIL for the rival marker.

This absence is distinct from ordinal rank: the same bundle does contain the exact ordinal `0xBAEE2` source and proves a valid rank anchor.

## Git history evidence

The source history gives a stronger regression boundary:

- `a22be86a3c83f9830a32de7d9dea23fbbdb8467a` (2026-10-09): explicitly states the projected rival marker was **already HMD-correct** and must be excluded from the new rank 1–5 R64 batch policy.
- `b0d6f977e793517a992c423b4b91ce3976e9c2c7` (2026-10-19): adds ordinal vehicle-rank anchor lift only and explicitly rejects applying it to `RivalMarker_sprani`.
- `3ed5290c90bbff5b98a5ca6d09ae66c8776464c8` (2026-10-20): changes only exact ordinal eye-cant provenance and documents that the HMD-proven rival remains on the previous identity-eye/IPD route.
- `0d25480814d064b096223d8f6b4b82feaeacea77` (2026-10-21): introduces extra R26-only rival detours at original E8 `0xBB6F0` and `0xBB796`.
- `a4790a0144603e30485c550d97c01570ae6418bc` (2026-10-21): restores the DX11-equivalent rival behavior by adding `RivalDx11NativeRoute=true` and conditionally **not installing** both detours. The setting is default true in `src/vr/settings.cpp` and `OutRun2006Tweaks.ini`.
- `03038d77b3d6254271ec6b7c0134f708bd0da27c` / `c24026d826399014e022a94098148fb513068953` (2026-10-22): remove the setting gate and force-install both rival detours again.

The checked-in review `docs/automation/reviews/DX9EX_R26_DX11_MARKER_PARITY_IMPLEMENTED_20261021.md` still defines `RivalDx11NativeRoute=true` as retaining the stock `BB6F0` projector and `BB796` rival sprite call. The current regression therefore violates the repository's own recorded policy.

## Fix

Restore the `a4790a01` installation boundary only:

- when `RivalDx11NativeRoute=true` (default), do **not** patch `0xBB6F0`;
- when `RivalDx11NativeRoute=true` (default), do **not** patch `0xBB796`;
- retain the old R26 detours behind `RivalDx11NativeRoute=false` for explicit A/B fallback;
- do not change ordinal rank `0xBAEE2`, rank projected-anchor ownership, rank eye-pose math, HUD scale, or C993/lens paths.

## Static validation

Before the fix, on source HEAD `135e4660b6f33e593c37bb2b841408611be9884e`:

`tools/verify_vr_rank_dx11_reference.py` fails because the expected `if (!Settings::VRRivalDx11NativeRoute.get())` installation guard is missing.

After the fix:

- `verify_vr_rank_dx11_reference.py`: PASS — `R26 DX11 rank direct projection, native rival + optional legacy routes, 0.55 HUD`.
- `verify_vr_dx9ex_launch_paths.py`: PASS.
- `verify_vr_20261020_hmd_baseline.py`: PASS.

`verify_vr_projected_marker_anchor.py` still reports its pre-existing signed clip-W policy mismatch; this fix does not modify that math.

Quest 3 / VDXR optical validation: **UNTESTED**.