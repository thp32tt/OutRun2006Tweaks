# Ferrari 365 GTS/4 Daytona — Slot A R41 native cockpit geometry continuation
2026-11-09 KST. **ACTIVE / NEEDS_REWORK**, **not vehicle COMPLETE**. Slot A ONLY.

## Source chain (immutable private files, no native export)
- Read-only original OutRun 2006 source: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Native PMT-derived original imported editable .blend: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Actual source import object names `object00_group01_material012_a0` (13v) and `object22_group00_material000_a0` (61v), verified by official Blender 4.5.15 opening source.
- Input existing real original-derived R40 private: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v38_r40.blend` SHA256 `e95bce97fc3e593577fef4db476d19f8a40fab22ad03dc5d1a922fc312ba6cce`.
- Photo private: `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`, genuine 1971 Daytona Spider LHD. Asset is research-only, not redistributed publicly.
- Checked `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv`: Daytona photo categories remain 1/8 no dedicated driver eye; 2/8 dashboard candidate, 3/8 instrument candidate, 4/8 steering candidate; center shifter, seats, doors, windshield frame missing dedicated authenticated viewpoints. The R41 comparison camera is **approximate, not the real game eye**, and seven view acceptance is incomplete.

## New material R41 source-edit evidence
Public non-proprietary editing script: `tools/car_modeling/slotA_daytona_r41_original_steering_spoke_dash_reprofile.py`, commit `6d8245d0f8c7c6fadcffdd9380a2086f365c9d36`, N100 exact script SHA256 `4fc58b26c2a94f071a21d223cbd716f3dcab0ba2a8c2ce456debd75061ac5b40`.

The script modifies **8 EXISTING original-derived objects** (no replacement object, added rim tube, from-scratch car or external GLB). It refines true metal spoke sheet relief without closing the original perforations, slight rim grip depth, sheet bridge end anchoring and original dashboard visor/pad/metal gauge recess geometry. It does not modify materials, UV, images, object transforms, animation pivots or original game assets.

| Edited existing PMT-derived object | Vertex / face count preserved | Moved vertex positions | Mesh geometry SHA256 before → after (prefix) |
|---|---:|---:|---|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885 / 3584 | 360 | `634fd1f2` → `167fd342` |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594 / 2592 | 2152 | `4e491e33` → `3c683058` |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157 / 5376 | 3127 | `d23b8431` → `4a4dbbaa` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9732 / 17300 | 8668 | `d49fa961` → `d65ea513` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144 / 6144 | 3187 | `a4f88bcb` → `e3ac0408` |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 | `10d71627` → `6a802c89` |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 | `ce137f12` → `85c08a6f` |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 | `b6a2ad23` → `34da9ce8` |

**Total 17,554 moved existing vertex coordinates.** Other 105 mesh SHA signatures unchanged. Original scene inventory and camera/pivots unchanged. Eight genuine wheel punched holes still open by independent source mesh and combined-object BVH raycasts. Source nonmanifold edges remain (pad 184, metal bezel 932, factory spoke 1601), not newly introduced. The **3 bridge mesh objects remain separate, not topologically welded**: this still fails the user's full physically connected steering wheel acceptance gate.

## Private actual .blend and independent rendering
- New **editable private R41 scene**: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v39_r41.blend`, 7,881,531 bytes, SHA256 **`65320b1ac94990a1c187f9e92d06e290ef46e6c89e6f9b6843e777a10041a236`**.
- Private machine-auditable per-mesh states `SLOTA_R41_SOURCE_WHEEL_DASH_AUDIT.json`, fresh independent reopen/Cycles audit `SLOTA_R41_FRESH_REOPEN_REAL_CYCLES.json`.
- Official Blender **4.5.15 LTS** independently reopened the **real private original-derived scene** in a fresh process and rendered 720×480, 3 spp Cycles with only 2 CPU threads. R41 PNG `SLOTA_DAYTONA_R41_AFTER_REAL_CYCLES_APPROX_EYE.png` SHA256 `ffc84734daeccc8530449e7f7c3711524ebd7cb5e9d43ec64cae923cb3785a64`.
- R40/R41 actual source-model before/after Cycles `SLOTA_DAYTONA_R40_R41_REAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `9e298c47a868a849f792e3760a1c1d48d799467db1cd0fe39d67202e30be70a9`, 16,004 / 345,600 RGB>3 pixels difference.
- GitHub Actions runner **does not have confidential original proprietary .blend**, so hosted *real-model* original-source Blender/independent-render gate is **BLOCKED_INPUT_NOT_TRANSFERRED**. Hosted public toolchain smoke (if successful) is NOT real original-scene QA. Do not say hosted original QA PASS or completed asset delivered by GitHub.
- Real game driver-eye pose, seven photo matched Spider viewpoints, full steering bridge weld and existing nonmanifold repair are **INCOMPLETE**; 24h allocation does not imply completion. Slot A remains Daytona ACTIVE/NEEDS_REWORK and **MUST NOT ADVANCE**.
- No OVC3/OVC/PMT/GLB output, game install, Quest/VR, outside body/wheels, texture/normal/PBR or modifications to Slot C F50, Dino, Model2 or other branches. Score this continuation **+0**, same incomplete Daytona P0 achievement; no retry/rollover/double counting.
