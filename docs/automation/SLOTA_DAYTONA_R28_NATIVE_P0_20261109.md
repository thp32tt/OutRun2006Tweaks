# Ferrari16 Slot A Daytona R28 original-source cockpit geometry checkpoint

2026-11-09 KST. Work on **only active_by_slot.A=daytona365**, `Ferrari 365 GTS/4 Daytona`. This is a physical vertex edit of eight previously-existing source-derived meshes in the original-game-backed R27 Blender file. No new car, GLB, objects, textures, normal/PBR maps, native/game export, VR or runtime source changes. Original PMT read-only.

## Source-of-truth and proof
- Original protected OutRun 2006 car PMT native file: `obj_plcar_dayts_pmt.sz` SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`, N100 `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/`.
- Verified native PMT original Blender import: `Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Raw imported original identity objects `object00_group01_material012_a0` (13 vertices/12 polygons) and `object22_group00_material000_a0` (61 vertices/31 polygons) independently opened with official Blender 4.5.15.
- Immutable previously edited original-game-derived input: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v25_r27.blend` SHA256 `3eef4b5106c324202612947ec99dda91f840564d3f755ad243260736f55549b4`.
- New private original-game-derived editable output: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v26_r28.blend` SHA256 `3f731eed475dbff71bc2e54dec4e1d1654dfbde0f29ce0f0ba6080700d19050a`.
- Existing real Ferrari 1971 Daytona Spider LHD interior photo (not uploaded publicly) SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`; source library `20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg`. Angles are not calibrated to game eye.

## In-place geometry changes

Target: recess excessive bright instrument lower crescent; gently curve existing binnacle upper shell; slim/refine original three-spoke wheel pressed-plate and outer grip; recess existing long front-lip/bright trim geometry that produces an overextended dash bar. Only existing vertex positions moved: topology, object identities, material slots, existing UVs, transforms and steering pivots preserved.

| Target | Original-derived Blender mesh object | Vertices/faces before → after | Moved vertices | Max Δ (m) | Mesh SHA256 prefix before → after |
|---|---|---:|---:|---:|---|
| upper | `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495/2816 → 1495/2816 | 278 | 0.00120754 | `0f7aac0f907a` → `31964e63f168` |
| face | `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 286 | 0.00233996 | `b9259f3560cb` → `71ef137b3d71` |
| cowl | `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2591 | 0.00269583 | `b23dbed7bec4` → `a8ffc795b12a` |
| bezel | `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157/5376 → 3157/5376 | 1866 | 0.00762607 | `cca2e6e63dec` → `34ef465464df` |
| spoke | `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 2186 | 0.00142623 | `d00674fc8f66` → `f21335c3e1c8` |
| rim | `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 6144 | 0.00083302 | `d2319d104ce5` → `89c4900ceb66` |
| lower_lip | `V8_2_CONTINUOUS_LOWER_DASH_LIP` | 60/58 → 60/58 | 60 | 0.0078339 | `79bfcf53284c` → `62e8bf80a152` |
| trim | `V8_2_DASH_TRIM_STRIP` | 8/6 → 8/6 | 8 | 0.0125873 | `a9b134dd8bac` → `9f820300d474` |

- Actual relocated source vertices: **13419** across 8 existing source-derived meshes. **105** other mesh geometric hashes unchanged; actual output contains no new meshes, curves, images or materials. Original camera and transforms unchanged.
- Original source-derived steering pressed-plate retained eight physically raycast-through holes (BVH PASS).

## Blender 4.5.15 and independent real-scene verification
- Official local N100 Blender 4.5.15 LTS saved a new immutable real R28 .blend and independently opened it in a separate process. Result SHA256 `3f731eed475dbff71bc2e54dec4e1d1654dfbde0f29ce0f0ba6080700d19050a` matches local filesystem hash.
- Actual Cycles 720 × 480, 3 samples, same **approximate** eye as R27, rendered PNG SHA256 `e89ad224afaf250c8034428295462652ad166caff5e9e0f1ab00878fd7c1d7bb`.
- R27-vs-R28 actual image >3 RGB difference: **12428 / 345600 pixels**, comparison SHA256 `0a9eb259016c2358fffe5cb38e2b6c2f0952e43fe97ceaad96089bb3401897fe`. Real rendered before/after path: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/SLOTA_DAYTONA_R27_R28_ACTUAL_CYCLES_BEFORE_AFTER.jpg`.
- Remaining known open edges: dashboard upper 172, face 184, bezel 932, original plate 1597. No claim of topology/manifold repair.

## Unmet completion gates and scope protections
- **Status stays `ACTIVE / NEEDS_REWORK`, not COMPLETE.** P0 geometry partial; original in-game camera is NOT calibrated and seven photo-matched Ferrari GTS/4 Spider views incomplete; current visual comparison is qualitative.
- GitHub Actions only has permission to execute source/queue/official Blender toolchain smoke. Genuine private .blend is **not transferred** to GitHub hosted runner: `BLOCKED_INPUT_NOT_TRANSFERRED`. Never label smoke as private-scene QA or car completion.
- No change to slot C F50, completed Dino246, game/VR/Model2 branches, exterior body/wheels/tires, textures, new materials, OVC3/OVC/PMT conversion, integration or packages.
- Slot A's 24h ownership is not finished/accepted merely by elapsed time; do not unlock another car.
- Previous AI2 score GitHub SSOT 2782 + this existing Daytona P0 follow-up 0 = **2782** (no duplicate credit for related geometry refinements, renders, smoke/retry).

## Private outputs
- `/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v26_r28.blend`
- `tools/car_modeling/slotA_daytona_r28_native_instrument_brow_trim_relief.py` (public non-proprietary source script; same copy N100)
- `SLOTA_R28_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json` and `SLOTA_R28_FRESH_REOPEN_REAL_CYCLES.json` (private N100 metadata)
- `SLOTA_DAYTONA_R27_R28_ACTUAL_CYCLES_BEFORE_AFTER.jpg` (private actual side-by-side render)
