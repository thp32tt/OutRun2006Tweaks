# Slot A — Daytona original-game cockpit R39 (2026-11-09 KST)

Status: **ACTIVE / P0 PARTIAL / hosted original-scene audit BLOCKED_INPUT_NOT_TRANSFERRED**. Vehicle remains `active_by_slot.A=daytona365`. Slot C/F50, Dino 246 and VR/runtime branches untouched. Only cockpit geometry.

## Read-only actual game lineage (private source files on N100)
- Native original OutRun 2006 resource: `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe` (unchanged, verified directly).
- First original PMT-derived imported Blender scene: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3` (unchanged, verified directly). Exact original mesh IDs `object00_group01_material012_a0` (13 vertices), `object22_group00_material000_a0` (61 vertices) validated by official Blender 4.5.15.
- Input *existing editable* original-derived cockpit: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v36_r38.blend` SHA256 `a6c92639d747a47b0f26e1fe166ca8075d10d857b31054ceeb3f311e2780f87f`.
- Actual private reference: `02_365_GTS4_Daytona/ADD_interior_LHD.jpg`, exact 1971 Ferrari 365 GTS/4 Spider LHD image in library MANIFEST, SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`, commercial proprietary rights: private reference only. Matrix other five dedicated photo category gaps remain.
- Correctly distinguish this exact Spider LHD shot from reference catalogue 365 GTB/4 coupe photos. Seven matching image angles are **not yet verified**.

## R39 actual original-derived Blender geometry modification
Public *editing script only*: `tools/car_modeling/slotA_daytona_r39_native_spoke_bridge_reanchor.py`, commit `05232dc99ce0ca155628b9b5294841adbd1102c7`, SHA256 `4dd15e9409d8c6a7d175617e1f1ed56910cee16dcad4a0ef6f6e6dfeacd421d0`. Executed on the read-only native-source-hash-gated private Blender scene, official Blender **4.5.15 LTS**.

The eight *existing source-derived Blender mesh objects* were modified **in place** by changing existing vertices, with unchanged vertex/face counts and unchanged UV, materials, world matrices and source scene inventory:

| Existing object | Vertices/faces before → after | Moved vertices | Before geometry SHA256 prefix → after prefix |
|---|---|---:|---|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 322 | `60d72231` → `88d181a5` |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2138 | `647ac4ff` → `c7fad9ad` |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157/5376 → 3157/5376 | 3157 | `c5957acb` → `d23b8431` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9732/17300 → 9732/17300 | 6998 | `e4edd16b` → `956adb5f` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 3730 | `9ca4a757` → `481d727b` |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 | `81f51ce1` → `10d71627` |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 | `7f117dec` → `ce137f12` |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 | `d66853b0` → `b6a2ad2` |

Core defect addressed: three inherited separate *sheet metal bridge* end loops visually floated from the real game-source steering pressing. Original vertices repositioned against actual source wheel/rim KDTree points, flattening/tapering inherited blocklike intermediate sections. Sum of per-terminal-loop nearest-vertex gaps:
- left: **0.0313774 m → 0.0007661 m**;
- right: **0.0381842 m → 0.0009363 m**;
- lower: **0.0604530 m → 0.0015028 m**.

**Important qualification:** this aligns/overlaps separate source-derived bridge terminal meshes visually; it is **not a welded manifold topology join**. Do not describe a seam as topologically repaired. 8 source wheel through-holes remain fully clear by true per-object-coordinate BVH rays. Existing non-manifold source edges remain unresolved. All **105 unrelated mesh signatures** identical; original source, packed historical image/material layers, camera, original wheel pivot unchanged. No new objects, textures, PBR, normal maps or outside body edits.

## Private edited .blend / independent actual render evidence
- Output editable `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v37_r39.blend` SHA256 **`85140adfa5fe3c57d79969b22df9c02a113ee22353adf4ba4b843e4839ae9db1`**.
- Separate official Blender 4.5.15 process reopened that *actual scene*, independently compared all eight changed source mesh signatures and 105 others, and Cycles-rendered 720×480 at the same approximate eye. PNG `SLOTA_DAYTONA_R39_AFTER_REAL_CYCLES_APPROX_EYE.png` SHA256 `37627aa4046dd63f085436eb98e54fcd991f31952d4cca305a133137976e1a8f`.
- True before R38 and after R39 Cycles two-panel `SLOTA_DAYTONA_R38_R39_REAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `4abb45eb105c8cb01359ece29968d9e5c5f765d325105267e2575d762523b2bc`. Pixel-difference threshold >3 RGB: **18,731 / 345,600**.
- Full per-object before/after SHA/vertex metrics: private N100 `SLOTA_R39_NATIVE_BRIDGE_DASH_GAUGE_AUDIT.json`. Fresh reopen QA: `SLOTA_R39_FRESH_REOPEN_REAL_CYCLES.json`.
- This comparison camera is APPROXIMATE, **not calibrated to actual game driver-eye FOV/pose**. Genuine matching seven-view photo validation, manifold fixes and 24-hour quality gate remain incomplete.
- GitHub Actions workflow can run **Blender 4.5.15 smoke/queue/source tests**, but an actual *hosted* original game model audit is **BLOCKED_INPUT_NOT_TRANSFERRED**: private licensed .blend is deliberately absent from the public repository. Never claim hosted full-model PASS.
- No PMT/OVC/OVC3 conversion or output, new vehicle model, GLB, game application, package, runtime/VR modifications or slot change. **Do not advance Daytona**.
- AI2 score delta: **+0** for continuing the same unfinished Daytona P0 / no new separately accepted quality achievement; do not double-count CI or rechecks.
