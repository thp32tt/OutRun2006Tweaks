# Slot A — Daytona original PMT-derived in-place cockpit geometry R27 (2026-11-08 KST)

**Status:** `ACTIVE / NEEDS_REWORK`, real source-backed P0 edit saved and local verification PASS, **vehicle completion NOT approved**.
**Queue:** `active_by_slot.A=daytona365`; F50 slot C, Dino246 and Model2/VR unaffected.

## Read-only provenance
- Protected OutRun 2006 native file: `obj_plcar_dayts_pmt.sz` SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Verified ORIGINAL native import: `Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- Original imported object names: `object00_group01_material012_a0`, `object22_group00_material000_a0`. Original source object00 = 13 vertices / 12 faces, object22 = 61 vertices / 31 faces.
- Immutable input R26 private source-derived .blend SHA256 `595b9f3676f8ba330cac3c1ee32fe8a0830a9d33cdc69b39dd25a386744279b9`.
- Immutable result R27 private editable .blend SHA256 `3eef4b5106c324202612947ec99dda91f840564d3f755ad243260736f55549b4`.
- Private exact 1971 Ferrari 365 GTS/4 Spider LHD interior photograph SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Source/attribution in N100 Daytona reference library. **No photo or proprietary native game/model files uploaded to GitHub.**

## Edits to existing original-derived meshes

| Feature | Existing Blender object identity | V before → after | Faces before → after | Vertices moved | Max displacement (m) | Mesh SHA256 prefix before → after |
|---|---|---:|---:|---:|---:|---|
| upper | `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495 → 1495 | 2816 → 2816 | 323 | 0.00155444 | `05f753537502` → `0f7aac0f907a` |
| face | `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885 → 1885 | 3584 → 3584 | 311 | 0.00244359 | `18afdc5296cc` → `b9259f3560cb` |
| cowl | `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594 → 2594 | 2592 → 2592 | 2594 | 0.00265518 | `c555cebf9dc3` → `b23dbed7bec4` |
| bezel | `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157 → 3157 | 5376 → 5376 | 2845 | 0.00265721 | `53b46ee24a9c` → `cca2e6e63dec` |
| spoke | `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720 → 9720 | 17285 → 17285 | 6075 | 0.00196191 | `92b10248fc24` → `d00674fc8f66` |
| rim | `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144 → 6144 | 6144 → 6144 | 6144 | 0.00097531 | `547db8faca93` → `d2319d104ce5` |
| hub | `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224 → 224 | 210 → 210 | 186 | 0.00138474 | `3adf5dd0335e` → `592172d533d4` |
| column | `V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES` | 100 → 100 | 82 → 82 | 92 | 0.00187637 | `8e782252cb72` → `faed810df464` |
| left_bridge | `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20 → 20 | 18 → 18 | 20 | 0.00157455 | `70b3470072ba` → `9316725d93c3` |
| right_bridge | `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20 → 20 | 18 → 18 | 20 | 0.00157455 | `ca6893bfaa49` → `2740788db749` |
| lower_bridge | `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20 → 20 | 18 → 18 | 20 | 0.00131345 | `80db087d1313` → `ee7901b215c1` |
| lower_lip | `V8_2_CONTINUOUS_LOWER_DASH_LIP` | 60 → 60 | 58 → 58 | 60 | 0.00458939 | `9f9783d8ce8d` → `79bfcf53284c` |
| trim | `V8_2_DASH_TRIM_STRIP` | 8 → 8 | 6 → 6 | 8 | 0.00547814 | `01324630e201` → `a9b134dd8bac` |

Total moved vertices: **18698** across 13 existing mesh objects; no new mesh/object/material/texture, no PBR/UV/camera/pivot changes. Non-target original-derived meshes: **100**, same geometry SHA.

## Real Blender QA and remaining blockers
- Official Blender **4.5.15 LTS** loaded the R26 existing scene, saved R27 as a new private `.blend`, and a **separate fresh process** reopened that R27 scene.
- Independent actual Cycles render **720×480 at 3 samples**: PNG SHA256 `aa7761d3502e2d80e34ed79e41e826c712bed931320315063c6f8df5dbbc66d4`. Same *approximate* driver-eye camera R26 vs R27: **12853 / 345600** pixels differ by >3 RGB levels; side-by-side comparison SHA256 `35114a9bd50d5b59c862528e56c7f5faf6b906776942328da4866f0e8d3c1de6`.
- Original game steering wheel source-derived eight through-holes preserved by actual Blender BVH ray-cast. Original source object IDs and matrices preserved.
- Existing nonmanifold boundaries **not fixed:** dashboard face 184, metal bezel 932, steering pressed plate 1597. These findings must not be described as repaired.
- Exact original in-game camera calibration: `NOT_CALIBRATED`; seven exact matching real Spider photo views: `INCOMPLETE` (reference matrix presently partial).
- Official GitHub Actions Blender 4.5.15 hosted **private-source audit**: `BLOCKED_INPUT_NOT_TRANSFERRED`; auto-triggered smoke, if successful, demonstrates toolchain/source tests only. No private .blend was uploaded into hosted runner.
- 24h slot A dedicated window ongoing; P0 dashboard+steering final photo-quality gate `NEEDS_REWORK`; no status advance.

## Private outputs (N100-only; no public proprietary asset redistribution)

- Editable .blend: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v25_r27.blend`
- Public script: `tools/car_modeling/slotA_daytona_r27_native_p0_camera_profile_relief.py` (same copy in N100 slot A directory)
- Before/after real render: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/SLOTA_DAYTONA_R26_R27_ACTUAL_CYCLES_BEFORE_AFTER.jpg`
- Private SHA/count audit: `SLOTA_R27_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json` and `SLOTA_R27_FRESH_REOPEN_REAL_CYCLES.json`.

**Forbidden operations intentionally not attempted:** OVC3/OVC/PMT export, original game rewrite, runtime/VR mod, game integration, package, car exterior/wheels, new textures, normal maps or PBR.

**AI2 score:** Github SSOT `AI_SCOREBOARD.md` latest confirmed 2782; previous **2782 + 0 = 2782 cumulative**. R27 follows the previously scored Daytona same-feature P0 work; save/reopen/render/CI/retry are not independently scored.
