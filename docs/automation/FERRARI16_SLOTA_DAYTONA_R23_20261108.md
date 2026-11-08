# Ferrari 365 GTS/4 Daytona — Slot A R23 original-source cockpit geometry checkpoint

Date: 2026-11-08 KST. Status: **ACTIVE / P0 PARTIAL; NOT COMPLETE**. Slot A only. No vehicle advancement or new score.

## Source lineage, read-only original

- Native OutRun 2006 game resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Native imported source: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Independently opened with official Blender 4.5.15 LTS: `object00_group01_material012_a0` (13 vertices), `object22_group00_material000_a0` (61 vertices) confirmed.
- Immutable edited input R22: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v20_r22.blend`, SHA256 `3c80b8b5491b727202a7f3370fd38ad369a34bd8914772af680e76253206bd11`.
- **Saved immutable R23**: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v21_r23.blend`, 7,863,797 bytes, SHA256 **`d88a2e3797a6e6867dd8354b004bb89f76a76d0ba42a17a88e76184f2fce0c70`**.
- Public non-proprietary editing source: `tools/car_modeling/slotA_daytona_r23_original_dashboard_steering_column.py`; private data is **not** uploaded to GitHub.

## Existing original-derived mesh edits — topology retained

All objects have unchanged names, world transforms, face/vertex topology, UV signatures, image/material registry, steering pivot and render camera. Only existing vertex positions changed. Full per-object before/after mesh SHA256 and matrices are in private `SLOTA_R23_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json`.

| Existing Blender object | Vertices / faces before → after | Moved vertices |
|---|---:|---:|
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495/2816 → 1495/2816 | 625 |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 584 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2127 |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157/5376 → 3157/5376 | 3157 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 7320 |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 6144 |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 → 224/210 | 140 |
| `V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES` | 100/82 → 100/82 | 77 |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 |

Total **20,234 moved original-derived vertices across 11 existing meshes**, 102 other meshes byte-equivalent by per-mesh signature. **Eight original steering spoke perforations remain open**, confirmed with Blender BVH ray tests before editing and after fresh reload.

## Actual fresh-process validation (private scene)

- Official Blender 4.5.15 LTS independently opened original imported game scene, R22 before, saved R23 after and fresh-reopened R23.
- Independent real private scene Cycles 720×480, 3 samples, sha256 `92caa5e731ad5df22957b0ed8f1be30a2165f6d5888aa00cb3f19309e6b866dd`.
- R22 vs R23 same **approximate (NOT calibrated game) camera** render shows **12,715 / 345,600 pixels** with a greater-than-three-channel RGB difference.
- Private before/after side-by-side `SLOTA_DAYTONA_R22_R23_ACTUAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `34edca7717a1bb92d7ed33f597d943b4650c3706ae4413f1662319598a5597e2`.
- Genuine 1971 Daytona Spider LHD privately held photo `ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb` from the approved N100 `MANIFEST.json`; no copyrighted image transferred. `COVERAGE_MATRIX_16x8.csv` still reports insufficient verified angle coverage.
- Existing nonmanifold edges persist in upper (172), padded fascia (184), bezel (932), factory steering pressing (1597). **No topology-cleanup pass claimed**.

## Outstanding gates, hard exclusions

**BLOCKED_INPUT_NOT_TRANSFERRED for GitHub-hosted real proprietary `.blend` QA**. GitHub Actions Blender smoke/source checks do not prove the N100 private original model was tested in Actions. Original game driver-eye/FOV, authentic exact-Spider seven-view photo match, nonmanifold repair, 24-hour allocation and P0 acceptance remain **INCOMPLETE**. No claim of complete vehicle or actual native game cockpit usability.

**No** external body/wheels/tires, texture/normal/PBR, GLB, OVC3/OVC/PMT conversion or output, game install, VR/runtime, slot C F50 or Dino246 changes. Original native files untouched. No score added for partial/repeated verification (**+0**).
