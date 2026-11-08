# SLOT A Daytona R37 — original-game-derived gauge and steering bridge geometry (2026-11-09 KST)

**Status: ACTIVE / NEEDS_REWORK. This is a local original-source geometry checkpoint, NOT Ferrari 365 GTS/4 completion.**

## Provenance and immutable inputs

- Slot A owner: `active_by_slot["A"] = "daytona365"`. Slot C F50 and completed Dino 246 **untouched**.
- Original native game PMT (read-only): `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- First authentic native PMT Blender import (read-only): `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- Native source object identities checked in independent official Blender 4.5.15 process: `object00_group01_material012_a0` (13 source vertices) and `object22_group00_material000_a0` (61 source vertices).
- Verified previous editable PMT-derived private scene: `fb8f676783b72f5933814f21f733944129500803a0b1e0b37ad1176c39336d3f` (R36, exact hash, immutable).
- Authenticated genuine 1971 LHD Daytona Spider private reference `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`, research-only, non-redistributable; checked `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv`. Seven photograph/eye viewpoints are **not** fully validated. Do not use replica/coupe photos as exact Spider geometry.

## R37 actual original-derived existing mesh edits

Existing dashboard visor and gauge bezel were rolled/recessed; factory 3-spoke metal sheet and grip rim got source-registered front-depth relief. Three **existing** short chrome bridge meshes had original source-rim/spoke endpoint vertex distances reduced without creating new connector objects or filling source wheel holes.

| Existing original-derived mesh object | Before V/F | After V/F | Moved source vertices | Geometry SHA256 before → after | Existing nonmanifold edges |
|---|---:|---:|---:|---:|---|---:|
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594 / 2592 | 2594 / 2592 | 2382 | `51eb784630105ee2fc96057bd2b0f5162a6c8656c2e99a3631e6f36ec8a7ec64` → `55469807a93b9c5aa9f7ec8a2e691156082628fbc5713e91e93f1554a7e68ef2` | 0 |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157 / 5376 | 3157 / 5376 | 2902 | `788e3c0f039bb06f882a79840c57c894d50df25597ff4c27c18716683c1bda09` → `83696e90fa462d4b9503a6dbff52ebe66a0fada452d83e8e85389be0325994ef` | 932 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9732 / 17300 | 9732 / 17300 | 4902 | `cccc7c94283d73c69bf8385ff4889018c5c2dac2c9b4c72d63f18bed33ed677f` → `de90b671d3c33c7991edfb5b205fe986c2c1ab3fd71597c882a1f62aef20f6d2` | 1601 |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144 / 6144 | 6144 / 6144 | 3410 | `d0fda73a526b061c8b40d0051a3766f64ed85ee394090d1c4ac2935bdd333803` → `11d53081dd785fb9abd2d78a8ed41f2f5d59b0f9294f0d5271229d3da1bf4c79` | 0 |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 / 18 | 20 | `e7a36d567651aac96378ff404abc3694152aacafef8a935a77ae83ef08fce7ee` → `386147fc2253ae5235a5cbdd172a25cf783c6c3f4a751a9fbc1909f0dfb3f657` | 0 |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 / 18 | 20 | `02981d836132487c5382ffddc7e13dc629f3fcbf070d72d730086dc507c2092d` → `493d4950ea9f645f4488d6adf7211a0698b8047bbd4d20cc1100a2d9cba2c465` | 0 |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 / 18 | 20 | `dc6f24aecdee273041649bbddd5f196295a0a6b2b4eb664ab77603c2e00c127d` → `d7973a3dd112b36024414d4c18e9a22bf44d7a6c42c069246e3718577cd39bcf` | 0 |

**Total physically modified vertices: 13656 in seven existing PMT-derived meshes.** Existing object IDs and mesh topology preserved. All **106 other mesh geometry signatures**, camera/steering pivot transforms, UVs, existing material and texture inventory unchanged. All original source-native **eight through-holes pass BVH ray validation**; source nonmanifold edges unchanged and **not healed**.

Source registration measurements (bridge endpoints):
- left: 48.41 mm → 40.139 mm (sum of sampled existing endpoint vertex-to-nearest-source vertex distances; **not** proof of watertight physical welding).
- right: 56.623 mm → 47.301 mm (sum of sampled existing endpoint vertex-to-nearest-source vertex distances; **not** proof of watertight physical welding).
- lower: 67.344 mm → 56.678 mm (sum of sampled existing endpoint vertex-to-nearest-source vertex distances; **not** proof of watertight physical welding).

## Private file and real Blender result

- Editable original-derived private R37 scene: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v35_r37.blend`
- Exact output SHA256: `bef16148b98554f0892b2aca080b7458139ebe4ee49d86a82d88a19cb551223e`. Original PMT/import/R36 remain unmodified.
- Reproducible Blender source script: `tools/car_modeling/slotA_daytona_r37_native_bridge_anchoring_gauge_roll.py`; N100 script SHA256 `d35587e55fe2e53cb8b20baeb8567a1fab4aae16defd83b3aaccadfdb13f6592`.
- Actual separate-process official Blender **4.5.15 LTS** reopened R37, verified seven before/after geometry signatures, the 106 unmodified signatures, source ID/camera/UV/material invariants, and eight through-holes.
- Actual local Cycles CPU render 720×480, 3 samples from identical **approximate, not game-calibrated** driver eye: `SLOTA_DAYTONA_R37_AFTER_REAL_CYCLES_APPROX_EYE.png`; SHA256 `ae74a7211f22c64771d828004d6491bc7d675e5b609edb9ae5c0804ac3b897f3`.
- True existing R36 versus newly saved R37 render comparison: `SLOTA_DAYTONA_R36_R37_REAL_CYCLES_BEFORE_AFTER.jpg`; SHA256 `c6cf61e90ae297cc6ef1b78c9723059797e18c06e5d4b67612fc3311a120eb22`; 9417 of 345600 RGB pixels changed by more than 3. This proves actual changed imagery only; **does not** prove photo fidelity.
- Private machine-readable audit: `SLOTA_R37_NATIVE_BRIDGE_DASH_GAUGE_AUDIT.json`; independent QA: `SLOTA_R37_FRESH_REOPEN_REAL_CYCLES.json`.

## Open gates / hard exclusions

- **BLOCKED_INPUT_NOT_TRANSFERRED**: licensed editable `.blend` is private on N100, not provided to hosted GitHub Actions. Hosted CI on GitHub can verify Python/queue/smoke only, **not** the real Daytona scene or source render. Never mark hosted real-scene audit PASS.
- **INCOMPLETE**: native game calibrated driver eye, seven authentic LHD Spider comparison viewpoints, source-existing nonmanifold fixes, photo-geometry human approval, complete 24h/quality acceptance. R37 is **not COMPLETE**; slot A stays Daytona, no next car transition.
- No native PMT/OVC/OVC3/GLB conversion or export, game installation, VR/Model2 change, other car/slot changes, exterior/body/wheels/tires, or material/texture/PBR/normal-map creation.
- Competition score delta **+0**: R37 continues existing Daytona P0 work; no duplicate credit from retry/rerender/CI.
