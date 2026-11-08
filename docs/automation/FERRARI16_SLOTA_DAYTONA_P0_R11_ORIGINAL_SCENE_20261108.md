# Ferrari16 slot A — original Daytona365 dashboard & steering R11
Updated: 2026-11-08 KST. State: **PARTIAL_NEEDS_QA**, NOT a completed vehicle.

Only source-of-truth queue `active_by_slot.A=daytona365` was worked. The pre-existing slot C F50 and Dino 246 are out of scope. No new car, fabricated GLB, game/VR change, proprietary file in public GitHub, PMT/OVC/OVC3 conversion/export, or new textures/PBR.

## Native original evidence (PRIVATE N100, no redistribution)
- Real OutRun 2006 PMT native input: `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`. Original game source was read-only.
- Verified first original-resource-derived Blender scene: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- Before editable native-derived scene: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v8_r10.blend` SHA256 `d18408d82e5de993f96ce882eff80e31eedf4b41468747785890e0942b2f6da9`.
- After edited private scene: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v9_r11.blend` SHA256 `2324f2e496d18073d8bd81433512a0a569f13936f0e8930dcb0ee8100723d026` (7498816 bytes). N100 `/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/`.
- Authenticated photo research input: private 1971 Ferrari 365 GTS/4 Spider LHD cockpit `02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. **Photograph viewpoint differs from the approximate Blender camera**, not a calibrated fit. Seven required authentic reference views are incomplete.

## Actual original-derived mesh geometry editing

Blender **4.5.15 LTS** opened the unmodified R10 private `.blend`, refined six **existing** original-derived cockpit meshes in-place in scene coordinates, retained all original object names/UV/materials/camera matrices/animation pivot, saved R11 privately, and a **separate fresh Blender process** reopened and inspected R11. Native original mesh identities are `object00_group01_material012_a0` and `object22_group00_material000_a0`; the R11 edits change the existing refined derivatives, not reconstructed replacement vehicles.

| Existing source-derived mesh | Before vertex/face | After vertex/face | Moved vertices | Max displacement |
|---|---:|---:|---:|---:|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` (dashboard) | 1885/3584 | 1885/3584 | 383 | 5.10391 mm |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` (brow) | 650/648 | 650/648 | 504 | 4.75079 mm |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` (bezel) | 908/1344 | 908/1344 | 908 | 0.80515 mm |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` (spoke) | 9720/17285 | 9720/17285 | 5894 | 3.30183 mm |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` (rim) | 1536/1536 | 1536/1536 | 224 | 1.89884 mm |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` (hub) | 224/210 | 224/210 | 133 | 2.06517 mm |
**Total moved existing vertices: 8046.** Geometry on 107 unrelated meshes remains hash-identical. Source-sourced wheel's **8 physical perforated holes** remain open in independent BVH front-ray verification. No mesh names added, no new material, no export. The baseline topological limitations were not repaired: dashboard 184, metal bezels 466 and original 3-spoke 1597 nonmanifold edges, all unchanged.

## Actual Blender real-scene QA
- Independent original-asset and R11 separate-process Blender 4.5.15 result: `SLOT_A_R11_GENUINE_NATIVE_BLENDER_FRESH_REOPEN_PASS`. Genuine modified geometry signatures and 107 other unchanged signatures checked.
- Actual private source Cycles rendering: `SLOTA_DAYTONA_R11_AFTER_REAL_CYCLES_APPROX_EYE.png`, SHA256 `0a169d07346c38bbc2b3892c75443c33f92e6970308269711d8728aa6d7a552d` (720×480, 3 samples, 2 CPU threads).
- One genuine Spider photo + real native R10/R11 same-approximate-eye Cycles side-by-side: `SLOTA_R11_PRIVATE_REAL_SPIDER_PHOTO_R10_R11.jpg`, SHA256 `092eba157d5f1595182ebd1192f3551f109b4450df5d33418ec2fd54627af408` (PRIVATE ONLY).
- R10 vs R11 difference image `SLOTA_R11_R10_R11_ACTUAL_CYCLES_PIXEL_DIFF.png`, SHA256 `e225462270b71f7e09e1b4a9872d23bf33078a4640d29f122fc50ed2553c30bf`: 12246/345600 pixels differ by more than 3 in some 8-bit RGB channel. This is geometry-change evidence, not real-car shape accuracy proof.
- Public source-only scripts live in `tools/car_modeling/slotA_daytona_r11_*.py`; no confidential original scene or photos uploaded.
- **GitHub-hosted 4.5.15 Actions real-private-scene audit = BLOCKED_INPUT_NOT_TRANSFERRED**. A default smoke SUCCESS does not count as real original mesh audit.
- Original game-calibrated driver-eye: NOT_VERIFIED; seven matching Spider photo/view checks: INCOMPLETE; 24-hour allocation and dashboard/steering visual QA not completed. Keep Daytona **ACTIVE**, `geometry_gate=PARTIAL_NEEDS_QA`; do NOT advance. Repeated work/rollover/CI/score: **+0; scoreboard unchanged**.
