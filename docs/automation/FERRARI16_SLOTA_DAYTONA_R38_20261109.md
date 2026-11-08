# Ferrari Daytona Spider, Slot A R38 — Original PMT-derived cockpit geometry

Date: 2026-11-09 KST. Branch: `feature/ferrari16-geometry-rework-20261108`. This is a **new private editable native-source geometry checkpoint** for `active_by_slot.A=daytona365`; **NOT** a completed car / native game build.

## Immutable input evidence

- OutRun 2006 read-only native resource `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Original native-PMT-import `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Separate official Blender 4.5.15 source-process verified **original** mesh IDs `object00_group01_material012_a0` 13 vertices, `object22_group00_material000_a0` 61 vertices. No substitute GLB or new car.
- Immutable source-backed R37 original-derivative `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v35_r37.blend` SHA256 `bef16148b98554f0892b2aca080b7458139ebe4ee49d86a82d88a19cb551223e`; original native PMT and first import unmodified.
- Existing privately held 1971 exact Daytona 365 GTS/4 Spider LHD `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Actual image inspected against previous and new model; N100 `MANIFEST.json` provenance and `COVERAGE_MATRIX_16x8.csv` checked. Photograph is private licensed reference, not embedded/publicly redistributed. Visual photo viewpoint still unmatched to calibrated native game camera.

## Material original-derived existing mesh edits

**Only in-place existing source-mesh coordinate edits**, no new objects, topology export, materials or textures. Original existing dashboard upper pad shoulder/visor/gauge bezel received slight structured curvature; native perforated wheel pressing and real rim received relief; original three **existing** metal spoke bridge objects were reprofiled toward native rim/metal sheet to reduce artificial disconnected appearance. They remain three separate mesh objects, **not** welded manifold geometry. Geometry changes are bounded rather than a fictional replacement wheel.

| Existing PMT-derived source mesh | Before vertices/faces | After vertices/faces | Moved vertices | Source geometry SHA256 before → after | Existing nonmanifold edges |
|---|---:|---:|---:|---|---:|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 | 1885/3584 | 322 | `fb4b56ae81d0a7d4b1e17c398646d5f7a796452622adb2a8df8e4e3e25da4ab1` → `60d7223105e6b59098f20377d2609f42810284dd2ebac0ee82cfbe895459a488` | 184 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 | 2594/2592 | 2138 | `55469807a93b9c5aa9f7ec8a2e691156082628fbc5713e91e93f1554a7e68ef2` → `647ac4ffef2f1c5d785742bfca66f64582d6679f6a8e1c48ac0c11d3d8c81718` | 0 |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157/5376 | 3157/5376 | 3157 | `83696e90fa462d4b9503a6dbff52ebe66a0fada452d83e8e85389be0325994ef` → `c5957acb796ffbcab073334ec6f47d54162be47aac49d43f40b1ef0aef0ab652` | 932 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9732/17300 | 9732/17300 | 6998 | `de90b671d3c33c7991edfb5b205fe986c2c1ab3fd71597c882a1f62aef20f6d2` → `e4edd16b181dff567dfd475545d79f31e6cbd5be5e8a95629409b9c380e8f38c` | 1601 |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 | 6144/6144 | 3730 | `11d53081dd785fb9abd2d78a8ed41f2f5d59b0f9294f0d5271229d3da1bf4c79` → `9ca4a757ddfa5373a916797cc06a02e15ce11ff426780b726e31f91302c5a970` | 0 |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 | 20/18 | 18 | `386147fc2253ae5235a5cbdd172a25cf783c6c3f4a751a9fbc1909f0dfb3f657` → `81f51ce1b8092afde031dffe5edbc89cecdf3fc6250d3f574755544f64511053` | 0 |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 | 20/18 | 18 | `493d4950ea9f645f4488d6adf7211a0698b8047bbd4d20cc1100a2d9cba2c465` → `7f117dec9faca15fd880fd53c2e4b1037fbdd56d288164efebb7ff2cfd8c4d04` | 0 |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 | 20/18 | 16 | `d7973a3dd112b36024414d4c18e9a22bf44d7a6c42c069246e3718577cd39bcf` → `d66853b092c18a54b383ada5a6083e87c454b50b92a94754ddbf6a9971999d4c` | 0 |

- **Total moved genuine existing vertices: 16397** on eight existing objects. `7673546e3a62347aaa312ab9021ab65f08f4eeafdae064fc0342dfd4bfaa1873` proves all **105** other mesh signatures identical.
- Source matrix, UV, camera, steering pivot, materials, image inventory unchanged. Eight native physically punched spoke holes preserved **including union of factory spoke + rim + three bridge meshes** using BVH ray tests. No new nonmanifold edges; **existing** dashboard 184, gauge bezel 932, spoke 1601 unresolved.
- Existing bridge source endpoint anchor-distance sum before→after (not proof of watertight welding): left 41.1750→29.2442 mm, right 48.3362→36.4690 mm, lower 56.6776→49.9245 mm.

## Immutable private artifact and local real-scene verification

- Real editable private Blender file: `/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v36_r38.blend` SHA256 **`a6c92639d747a47b0f26e1fe166ca8075d10d857b31054ceeb3f311e2780f87f`** (7,879,096 bytes). Preserved R37 and original input SHA; did not overwrite.
- Public nonproprietary geometry editor: `tools/car_modeling/slotA_daytona_r38_native_wheel_sheet_gauge_arch.py` SHA256 **`1f0c70e3c944dc81ba1b42132fc9470581864c353321665370d86d63f036c5a4`**, material source commit `be138afe8e137577d7900467c32bfcfdbdebb911`.
- Official Blender **4.5.15 LTS**: independently opened immutable first original import, opened R37, physically changed eight original-derived meshes, saved R38; a second fresh Blender process independently opened the exact R38 .blend, verified 8 after-signatures, other 105 source objects, UV/material/camera and 8 union-hole BVH checks. **Local private actual-scene PASS**.
- Real CPU Cycles render 720×480 (3 samples, equal approximate eye) `SLOTA_DAYTONA_R38_AFTER_REAL_CYCLES_APPROX_EYE.png` SHA256 `5c8dcd3ea831b087ebd0a1649b3761e540b67eb3cf0b255af0484f6055df17b4`.
- Real same-angle R37/R38 before/after file `SLOTA_DAYTONA_R37_R38_REAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `137978a806e6b41b63eba1f593002bb03d7f7ceee23fc02c71f00bb1867486d5`, 17111 of 345,600 pixels had RGB delta greater than 3; actual image change, **NOT evidence of exact reference fidelity**.
- Private audit `SLOTA_R38_NATIVE_BRIDGE_DASH_GAUGE_AUDIT.json`, second-process render QA `SLOTA_R38_FRESH_REOPEN_REAL_CYCLES.json`.

## Fail-closed QA and exclusions

**BLOCKED_INPUT_NOT_TRANSFERRED:** proprietary original-derived editable .blend was NOT transferred to GitHub hosted runner. GitHub Actions 4.5.15 on public source may prove toolchain smoke/regressions only, **not a hosted real-original-scene render PASS**. Do not mark car completed.

**INCOMPLETE:** original in-game driver-eye / steering animation calibration, seven photo-matched genuine Spider views, source inherited nonmanifold repairs, final human-audited dashboard+wheel quality, 24h acceptance/QA. No car transition; A=daytona365 remains `ACTIVE / NEEDS_REWORK`. Source mesh render is low-sample approximate-camera evidence.

**Hard exclusions held:** No OVC3/OVC/PMT conversion or output, no GLB/replacement, no external body/wheels/tires, texture/DDS/normal/PBR materials, game deployment, Model2/VR/DX11/DX9Ex/DXVK or Dino, F50/slot C edits. N100 existing private original and photos remain private.

**AI2 scoreboard:** latest confirmed 2782 + same ongoing Daytona P0 continuation **0** = 2782; no score for repeated render, audit, CI or rollover.
