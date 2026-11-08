# Ferrari 365 GTS/4 Daytona — Slot A R29 native-source cockpit geometry

Date: 2026-11-09 KST. Slot A only: `active_by_slot.A=daytona365`. Retain `ACTIVE/NEEDS_REWORK`; 24h allocation and P0 acceptance still incomplete.

## Mandatory original-game provenance

- Read-only OutRun 2006 native resource `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe` (independently rehashed).
- Original PMT-derived imported Blender scene `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`; original imported IDs verified by independent official Blender 4.5.15: `object00_group01_material012_a0` (13 vertices) and `object22_group00_material000_a0` (61 vertices).
- Immutable R28 source-backed input `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v26_r28.blend`, SHA256 `3f731eed475dbff71bc2e54dec4e1d1654dfbde0f29ce0f0ba6080700d19050a`.
- **New editable private R29** `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v27_r29.blend`, SHA256 `8383d235ca0dbfa89f541ebe3681bbcaea6df65c57dda4fa8a7834f738253e36` (7,877,951 bytes). Stored only under `/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/` — not uploaded to GitHub.
- Actual 1971 Ferrari Daytona Spider left-hand-drive reference `02_365_GTS4_Daytona/ADD_interior_LHD.jpg`, private SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Uncalibrated photo viewpoint: use for qualitative shape comparison, not metric alignment.

## In-place 3D geometry changes

Actual existing source-derived mesh vertex-position edits: **14,650 vertices across 10 existing mesh objects**, with original topology, UV, materials, camera world matrices, object inventory and wheel pivots preserved. The **other 103 original-derived meshes** are byte-signature invariant in the source geometry check.

| Existing mesh name | Vertices / polygons (unchanged) | Moved vertices | Before → after mesh SHA256 prefix |
|---|---:|---:|---|
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495 / 2816 | 326 | `31964e63` → `6a6185d4` |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885 / 3584 | 309 | `71ef137b` → `e18e74bf` |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594 / 2592 | 2594 | `a8ffc795` → `62be9afc` |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157 / 5376 | 1670 | `34ef4654` → `5010e42e` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720 / 17285 | 3311 | `f21335c3` → `e8de7939` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144 / 6144 | 6144 | `89c4900c` → `b201d5ba` |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224 / 210 | 214 | `592172d5` → `8dc59831` |
| `V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES` | 100 / 82 | 42 | `faed810d` → `6af4aea3` |
| `V8_2_CONTINUOUS_LOWER_DASH_LIP` | 60 / 58 | 32 | `62e8bf80` → `a23e3dc4` |
| `V8_2_DASH_TRIM_STRIP` | 8 / 6 | 8 | `9f820300` → `c9dad9be` |

Changes: curved/recessed existing instrument cowl, lower chrome gauge crescent and padded dash; reshaped 3-spoke pressed-metal profile, steering ring cross-section, original hub and column shoulders; retreated pre-existing lower dashboard lip/trim. No other vehicle or complete cockpit generated, no GLB, and no exterior changes.

## Real Blender QA / private proof

- Original imported scene independently reopened; separate official **Blender 4.5.15 LTS** processes built immutable R29 and freshly reopened R29, checking saved geometry hashes, source IDs, inventories, masks and original eight physically raycast-open steering spoke perforations.
- Actual 720 × 480 Cycles render (CPU, 3 samples), private `SLOTA_DAYTONA_R29_AFTER_REAL_CYCLES_APPROX_EYE.png` SHA256 `1030343842abdde6abaf88b4490896e7154c1c9f47e3d892866c1a50a67064c1`.
- Private R28/R29 side-by-side real scene render `SLOTA_DAYTONA_R28_R29_ACTUAL_CYCLES_BEFORE_AFTER.jpg`, SHA256 `7b41b26d5833ae915250f87f4e53d211f3198f52b4e4e1002018f8007fe88d9c`, **11,964 pixels** with max RGB difference greater than 3.
- Full original/edited per-object mesh digests and topology counts on N100 `SLOTA_R29_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json`; fresh-reopen findings `SLOTA_R29_FRESH_REOPEN_REAL_CYCLES.json`.
- Remaining inherited non-manifold/open edges: dash upper 172, padded face 184, bezel 932, original 3-spoke 1,597 (other named targets 0); no false repair assertion.

## Gating, security and score

- Original in-game driver eye is not calibrated; seven authentic camera-aligned Spider LHD reference comparisons incomplete; P0 human visual acceptance remains partial. **Vehicle not complete, no next car.**
- GitHub-hosted real private-scene `.blend` audit: `BLOCKED_INPUT_NOT_TRANSFERRED`. GitHub Actions source/queue tests and official Blender smoke are not evidence of native private asset rendering. Original game PMT/.blend/private photos must not be committed to public GitHub.
- This is a continuation of the already-scored Daytona P0 rework, not a new independent achievement: **AI2 score delta +0**. Do not modify AI_SCOREBOARD.md based on render/source retry alone.
- No OVC3/OVC/PMT conversion/export, packaging, game/VR/runtime, materials/textures/normal/PBR, exterior or Dino/F50/Model2 changes.
