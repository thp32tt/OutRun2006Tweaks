# Ferrari 365 GTS/4 Daytona — Slot A original source-derived cockpit R40
Date: 2026-11-09 KST. **Status: ACTIVE / P0 partial, not complete.** This is an in-place modification of the existing original OutRun 2006 cockpit scene, not a generated or converted substitute. Other slots and all game/runtime branches excluded.

## Original source / private provenance
- Actual original read-only game asset `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`, independently rehashed.
- First actual original-game PMT imported Blender scene `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`, independently rehashed. Verified original raw mesh names `object00_group01_material012_a0` (13 vertices) and `object22_group00_material000_a0` (61 vertices) through actual official Blender 4.5.15 import reopen.
- Existing, verified original-derived R39 private input: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v37_r39.blend` SHA256 `85140adfa5fe3c57d79969b22df9c02a113ee22353adf4ba4b843e4839ae9db1`, preserved immutable.
- Private original-variant reference image `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg` actual 1971 Spider LHD, SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`, copyright/private photograph **not public**. Comparison view is uncalibrated; `COVERAGE_MATRIX_16x8.csv` still lacks all 7 independently authenticated photo-matched viewpoints.

## New existing-mesh geometry work
Public Blender editing source **only**: `tools/car_modeling/slotA_daytona_r40_native_dash_fairing_spoke_relief.py` GitHub material commit `e9bc0ea3ee9cb8d8fa15217c62568e52d5a6b901`, source SHA256 `2e4bc9fcc40892f0370b6e28f4eaaf45fbacc2ae2342b0c883949bb8442effc7`.

An actual R39 Blender cockpit image ray-cast identified the protruding straight center under-stack shelf: `V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING` at pixel (488,344) in the explicitly approximate 720×480 driver view. R40 recesses and tapers its **existing** sixteen vertices; no replacement object, pipe or new primitive. In the same **existing original PMT-derived scene**, it reshapes the real instrument brow/upper dashboard, pads and factory three-spoke pressing depth, and adjusts existing rim and hub collar cross-sections. Physical vertex changes are logged with per-object original identifiers and exact before/after geometric SHA256 in private `SLOTA_R40_NATIVE_BRIDGE_DASH_GAUGE_AUDIT.json`.

| Existing original-derived mesh object | before vertices/faces → after vertices/faces | positions changed | geometry SHA prefix before → after |
|---|---|---:|---|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 456 | `88d181a5` → `634fd1f2` |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2113 | `c7fad9ad` → `4e491e33` |
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495/2816 → 1495/2816 | 485 | `dde69f0f` → `197e69df` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9732/17300 → 9732/17300 | 7986 | `956adb5f` → `d49fa961` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 3036 | `481d727b` → `a4f88bcb` |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 → 224/210 | 21 | `62b3c58c` → `8a4ae78e` |
| `V8_6_SOURCE_BOUNDED_LOWER_STACK_FAIRING` | 16/14 → 16/14 | 16 | `1b595e95` → `f6a21132` |

**Total 14,113 existing vertex positions changed across 7 original-derived meshes.** All 106 other meshes' geometry SHA unchanged, and scene inventory, original camera, original wheel pivot/axes, world matrices, UVs, existing materials/images unchanged. All existing native 8 spoke through-holes remain open by actual transformed-object BVH ray-casts. Original dashboard 184, upper dash 172, factory wheel 1601, lower-stack 4 nonmanifold edges are *inherited/unresolved*, **not** repaired/worsened in R40. R39 visual bridge tip contact remains **not welded into a single watertight shell**.

## Private actual editable scene / QA, not a public asset
- Final private **editable .blend only**: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v38_r40.blend` SHA256 **`e95bce97fc3e593577fef4db476d19f8a40fab22ad03dc5d1a922fc312ba6cce`**.
- Separate actual **official Blender 4.5.15** process independently reopened *this real private licensed original-derived scene*, verified all seven exact post-edit signatures and 106 untouched mesh signatures, and rendered real Cycles 720×480 3spp at the same **approximate, NOT actual original game calibrated eye**.
- Private new Cycles `SLOTA_DAYTONA_R40_AFTER_REAL_CYCLES_APPROX_EYE.png` SHA256 `3722e798efdfdce010f49d11cdb5890e076100606f291177302743b173891ed2`.
- Private actual R39/R40 two-panel Cycles comparison `SLOTA_DAYTONA_R39_R40_REAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `4336b06bc1ed731794e17cd177442097a35177982cde3aeb7e7523f6c3833981`. Changed pixels RGB>3: **13,394/345,600**; 720×480 same camera and rendering settings. Comparison is real model images, **not** a simulation or generated concept. Scene file hash remains unchanged by render, as temporary camera was never saved.
- Hosted GitHub Actions original proprietary `.blend` audit remains **BLOCKED_INPUT_NOT_TRANSFERRED**. Hosted Blender 4.5.15 smoke/queue tests, if passing, are only smoke (no confidential original input on runner), never completion evidence.
- Remaining acceptance work: calibrated actual original game driver-eye FOV/pose, 7 exact photographed Spider reference views and matching Blender renders, prior non-manifold source defects, 24-hour quality gate, steering bridge manifold connection. **Do not mark COMPLETE / do not advance to another vehicle.**
- **No OVC3/OVC/PMT/GLB conversion/output, game application, VR/Model2/Dino/slot C, exterior body/wheels, new textures/normal/PBR or other branches.** Only allowed edited source-derived .blend stays on private N100.
- Score **+0**: same ongoing incomplete Daytona dashboard/wheel achievement; no duplicate credit for source follow-on, CI, render, recheck or rollover.
