# Slot A — Daytona R21 original PMT-derived cockpit topology checkpoint
Date: 2026-11-08 KST. Slot A only; no car advancement, no runtime work.
Base GitHub tree: `50db84223e1c4fe9afd235ab09fed11231b7378b` (queue optimistic-write parent).

## Input origin and SHA-256
- Read-only OutRun 2006 `obj_plcar_dayts_pmt.sz`: `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Protected source import `Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`: `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- Raw native importer original object IDs: `object00_group01_material012_a0` (13 vertices / 12 faces); `object22_group00_material000_a0` (61 vertices / 31 faces). Following derivative meshes have original provenance but are **not** byte-identical PMT raw topology.
- Private native-derived R20 input: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v18_r20.blend` SHA `0e0d403e512d4f4612817fb71b9796fc84f2f58cc52b9b3625497727fbab8fcd`.
- Actual 1971 Daytona Spider LHD private photo used for visual reference: SHA `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`; 7-view exact-model validation **incomplete**.

## New real geometry edits (existing mesh objects only)
| Source-derived Blender object | Before | After | Changed vertices |
|---|---|---|---:|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885 v / 3584 f | 1885 v / 3584 f | 633 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594 v / 2592 f | 2594 v / 2592 f | 2100 |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 8 v / 6 f | 20 v / 18 f | 12 |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 8 v / 6 f | 20 v / 18 f | 12 |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 8 v / 6 f | 20 v / 18 f | 12 |

Blender bmesh inserted 3 longitudinal cuts into each pre-existing stamped bridge object and tapered/crowned its actual faces; sculpted only existing padded dashboard and binnacle vertices. **108 other mesh signatures unchanged**, no new objects/material/texture/PBR/normal map, no object transform, camera, original wheel pivot, original steering holes (8/8), PMT export, OVC/OVC3/GLB export or game/VR changes.

## Private deliverables (never publish proprietary scenes/photos)
- `/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v19_r21.blend`
- New editable scene SHA-256: `581ef8d73f36b18c559b97d5f50867da0002b1abf4c76335a5d732ab917b4938`.
- Private separate-process Blender 4.5.15 LTS reopen + actual Cycles (720x480, 3 samples) render `SLOTA_DAYTONA_R21_AFTER_REAL_CYCLES_APPROX_EYE.png`, SHA `6e5f3079a2872a09f39d330f8648cbbdd9acb933a28c00c7e86b277532e0f070`.
- Direct private R20/R21 render comparison `SLOTA_R20_R21_NATIVE_CYCLES_BEFORE_AFTER_PRIVATE.jpg`; 1,804 / 345,600 pixels differ by >3 on max RGB channel. Both use the **same approximate eye**, not the game's calibrated camera.
- Audit JSONs `SLOTA_R21_NATIVE_DASH_BRIDGE_TOPOLOGY.json`, `SLOTA_R21_FRESH_REOPEN_CYCLES.json`, `SLOTA_R21_PHOTO_GEOMETRY_COMPARE.json`.

## Gates / disposition
- Genuine non-public source read/check and independent private Blender **PASS**.
- Existing source nonmanifold dashboard 184, factory 3-spoke 1597 remain; newly subdivided bridge parts 0 nonmanifold each.
- GitHub Actions 4.5.15 **original private .blend not transferred to hosted runner** → `BLOCKED_INPUT_NOT_TRANSFERRED`. Do **not** equate toolchain smoke with real source-scene CI; no completion claim.
- Exact original-game driver-eye pose calibration, 7 exact Spider views and 24h allocation pending. Remain `ACTIVE/PARTIAL_NEEDS_QA`; score change **+0** (no same-work retry/rollover credit).
