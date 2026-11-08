# Ferrari Daytona 365 GTS/4 — SLOT A R36 original-PMT-derived P0 dashboard/steering geometry

Date: 2026-11-09 KST. Slot A car ownership = `daytona365`, state ACTIVE/NEEDS_REWORK. This is a new editable Blender source-geometry checkpoint, **not** vehicle acceptance.

## Original game resource and guarded input

- Original OutRun 2006 asset (read-only): `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`; SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Exact first original PMT-import scene (read-only): `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`; SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- The actual first native Blender 4.5.15 source was independently opened, and mesh IDs `object00_group01_material012_a0` (13v) and `object22_group00_material000_a0` (61v) were asserted. These are original source nodes, not an invented new car or substitute GLB.
- Authenticated exact 1971 Ferrari 365 GTS/4 Daytona Spider LHD private reference: `/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg`; SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Copyright photo remains private; original photos in `MANIFEST.json` / `COVERAGE_MATRIX_16x8.csv` are research-only; not seven-view validated.
- Immutable previous source-backed R35: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v33_r35.blend` SHA256 `e64722b0d72fe79ade93bae0c03dc97771db585020440e85e5f7765455155c9f`.

## Existing source-geometry edit (no replacement object)

Refined native-source instrument upper brow, dashboard pad front shoulder, recessed gauge metal bezel, original 3-spoke pressing and lower instrument shroud. Original mesh topology, object IDs, world transforms, camera/steering pivots, UVs, existing materials and all textures were preserved. No alternate vehicle/GLB, no brand-new dashboard or steering creation.

| Existing object name | Before topology | After topology | Moved vertices | Geometry SHA256 before → after | Pre-existing nonmanifold edges |
|---|---:|---:|---:|---|---:|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885v/3584f | 1885v/3584f | 323 | `f760bd453002083903939c926c966a5f8c038c28862ef89911b2664591e28486` → `fb4b56ae81d0a7d4b1e17c398646d5f7a796452622adb2a8df8e4e3e25da4ab1` | 184 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594v/2592f | 2594v/2592f | 2153 | `745e08ff8c32fe199faf3ff6804250b496b122873bff96f3afb4527bdb78ab5b` → `51eb784630105ee2fc96057bd2b0f5162a6c8656c2e99a3631e6f36ec8a7ec64` | 0 |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157v/5376f | 3157v/5376f | 2387 | `e6862a7e6b5dc616de9e83b14227002baf2234cf67bcfc0368e05b99e1e23c0f` → `788e3c0f039bb06f882a79840c57c894d50df25597ff4c27c18716683c1bda09` | 932 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9732v/17300f | 9732v/17300f | 2507 | `3a8d0c6d788b3b2cddc254e9a3c62f51abbd8569ebc7ecad1667de598682f583` → `cccc7c94283d73c69bf8385ff4889018c5c2dac2c9b4c72d63f18bed33ed677f` | 1601 |
| `V8_21_SOURCE_LOWER_GAUGE_SHROUD` | 168v/162f | 168v/162f | 144 | `0d800a2c89d03e0ec46e874c1a28ae593069938835e4698acb007d6de35d3dfd` → `7d45d2c8dec4ecf17fefea3880fdf0e99659b9392cbf495a858726b9aed71db0` | 0 |

- **7,514 real original-derived vertex coordinates physically changed** across exactly five existing cockpit P0 meshes.
- Other **108** mesh geometry signatures unchanged (aggregate SHA256 `829e44ef56a8fe4407cecb6bf7914d74e3762cc362ea330aecd312ee87396c39`).
- Original steering eight true through-holes preserved before geometry build and again after native scene save/reopen using BVH ray checks.
- No materials/textures/PBR/normal map creation, no outside body, exterior wheels or tires, no exports to PMT/OVC/OVC3/GLB, no game build/installation or VR/Model2/Dino/F50 edits.

## Private editable saved output and independent real-scene verification

- Private immutable edited scene: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v34_r36.blend`
- SHA256: `fb8f676783b72f5933814f21f733944129500803a0b1e0b37ad1176c39336d3f` (7,881,459 bytes).
- Reproducible nonproprietary source script: `tools/car_modeling/slotA_daytona_r36_native_dash_cowl_steering_sculpt.py`; local SHA256 `89c21021003f86921082dc83540b66919243fa24985ed204e719774ebfca441f`.
- Actual official **local** Blender 4.5.15 LTS loaded R35, saved R36, a **separate Blender 4.5.15 process reopened the R36 SHA**, verified every affected original-derived mesh signature and all protected signatures; CPU Cycles 720x480, 3 samples real rendered PNG SHA256 `b92c7454373eafc073f6a8b3611076d7e78fb5d66884091247b8ed4b7fcb70d9`.
- Actual R35 vs R36 same approximate driver-eye Cycles before/after: 8,141 / 345,600 RGB>3 pixels changed. Comparison `SLOTA_DAYTONA_R35_R36_REAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `7a115aadaeb771faac098d007c72889ddeef10b62c7c56f345da925d8fdfe6cd`.
- Private exact audit `SLOTA_R36_ORIGINAL_SOURCE_DASH_STEERING_AUDIT.json`; fresh-reopen QA `SLOTA_R36_FRESH_REOPEN_REAL_CYCLES.json`; actual render/comparison stored only under N100 work_handoff; licensed asset .blend/photos **not** publicly committed.
- Local visual comparison is approximate-eye and reference photo is not camera-registered. Pixel differences establish scene change only, **not** photo fidelity passing.

## Gates / no misleading completion claim

- **PASS (local)**: hashed read-only native PMT, genuine original import, guarded R35 input, real existing original-derived geometry edit, local Blender 4.5.15 save / independent fresh reopen / Cycles, original steering holes and unrelated-mesh protection.
- **INCOMPLETE**: original game driver-eye calibration, seven authentic exact Spider LHD photo-angle comparisons, pre-existing source non-manifold geometry repair, final human P0 dashboard/steering photo-fidelity acceptance.
- **BLOCKED_INPUT_NOT_TRANSFERRED**: licensed private .blend not provided to hosted GitHub Actions. Official hosted Blender 4.5.15 can only run smoke/queue-contract tests; **do not claim hosted real-scene pass** or completion.
- User delivery of private editable R36 .blend has not been separately verified.
- **NO ADVANCE**: `active_by_slot["A"]="daytona365"`, vehicle `ACTIVE / NEEDS_REWORK` even if 24h elapsed. No duplicate score: prior AI2 2782 + 0 = 2782.
