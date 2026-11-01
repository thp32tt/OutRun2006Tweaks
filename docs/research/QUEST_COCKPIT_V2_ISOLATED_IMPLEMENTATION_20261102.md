# QuestCockpitV2 isolated implementation branch — 2026-11-02

Branch: `vr-quest-cockpit-v2`; forked exactly from stable DX9Ex `9c4dec84748b3c7dde99a8cb4f26b3de2eb2503b`.
The established `vr-d3d9ex-focus` and published `v0.01-beta` are unchanged.

## Implemented on the isolated branch

- Retired ACTIVE legacy `DriverSeatView` camera-offset/last-valid-pose latch, force-full-car detour, 1.15 vehicle-scale detour, global glass probe and ambiguous driver/heroine suppression hook; their research files remain archived, not compiled into gameplay.
- New production C++17 `src/vr/game/quest_cockpit_v2_runtime.hpp`: original Quest camera mode-1 admission contract, single verified-native-game-frame/key admission, player identity, XR pose and space generation, stereo+position tracking validation, same-frame fail-closed latch, 16+16 B0/F0 vehicle copies, independently tested ARM64-derived affine occupant correction, renderer-local F0 identity transaction that restores on exception. Output is a reflection and must NEVER be applied to HMD view/culling.
- Player-car original PC EXE RVA `0x69764` is now a **read-only** diagnostic observer; only when `CockpitFrameProbe=true`. It captures real player B0/F0 and computes a correction candidate, emitting bounded 32 samples only if Telemetry is separately enabled. There is **no** car flag, camera, glass, driver, FFB, or physics mutation.
- Separate deterministic C++17 smoke test + new branch-only CI and Windows Win32 game DLL / x64 OpenXR host compile workflow. Normal INI debug and release logging remain off.
- Shared `RestoreCarBaseShadow` GAME/GOAL/START65 predicate preserved, core `FixZBufferPrecision` and SceneEffect re-entrant exclusion preserved. Retiring cockpit leaves native non-cockpit R26 rendering.

## Incomplete (not presented as functional cockpit)

Original PC native `frame_render_449050` at EXE RVA `0x49050` is *known from binary research*, but exact active executable signature, entry/leave trace, player callback `0x9F3E0` to XR frame relationship are **not proven by a Quest3/Windows capture**. `FrameOwner` thus cannot be admitted into gameplay. The V2 seat anchor/vehicle draw/occupant model commit are **not enabled**. These require read-only original game-frame trace, actual native camera mode-1 per-car seat table, complete atomic camera-car-occupant same-frame rendering and Quest3 in-headset stability evidence. This branch is a **dev branch, not a release**. Legacy settings were deliberately removed, so old diagnostic `DriverSeatView=true` command-line arguments are not supported here.

Next: verify original PC frame callback entry/exit signature, add original-frame counter correlation, then implement a scoped, player-only V2 car+driver path using exactly one XR pose and correct native seat table. Never infer game-frame id from Present or reuse a stale camera pose, and never silently activate the old cockpit.

## Native original frame scope tracer (second implementation commit)
- Retail executable prefix 24 bytes were retrieved directly from the user's authorized N100 source `apk/_analysis_focus/quest_v2_pc_exe_entry_prologues_20261026.json`; no EXE or table bytes committed to the repo.
- New opt-in, signature-checked x86 midhooks: `frame_render_449050` RVA `0x49050`, `frame_end_448E40` RVA `0x48E40`, and original player callback `0x49F3E0` RVA `0x9F3E0`. Three signatures checked before installing the atomic triad. Any unsupported/existing-patched exe fails closed and leaves normal rendering unchanged.
- Independent C++17 native-frame tracker counts entry/exit, nested/stray callbacks, source player callback and original verified player-car draw, then correlates native epoch and D3D9 Begin/End/Present + XR pose on the *same thread*. Same-thread observations are not proof of one-to-one frame ownership: `frameToPoseVerified=0` remains explicit until HMD field evidence. Bounded first 64 + power-of-two logs and reset invalidate; all logging remains opt-in.
- This is verified entry provenance **only**, not enabled cockpit seat rendering. The original Quest mode-1 per-car camera table and XR-frame correlation must be validated before new player model and occupant correction can be committed.
