# Slot A — Ferrari 365 GTS/4 Daytona R22 original-native cockpit geometry

Date: 2026-11-08 KST. Slot A sole vehicle `daytona365`. GitHub input HEAD `5f2e9cf7d6700dedef00674172beeb2f4a8bd202`.

## Source asset and editable scene provenance
- Original read-only OutRun 2006 vehicle: `Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`. No writes to this source.
- Original imported native scene: `Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Native imported object IDs `object00_group01_material012_a0` (13v/12f), `object22_group00_material000_a0` (61v/31f). Working scene contains genuinely source-**derived** meshes, not byte-identical raw PMT faces.
- Private R21 input `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v19_r21.blend`, SHA256 `581ef8d73f36b18c559b97d5f50867da0002b1abf4c76335a5d732ab917b4938`.
- N100 official Blender 4.5.15 LTS opened R21, edited existing geometry, saved private R22 `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v20_r22.blend` SHA256 **`3c80b8b5491b727202a7f3370fd38ad369a34bd8914772af680e76253206bd11`**.
- Photo source `02_365_GTS4_Daytona/ADD_interior_LHD.jpg` (1971 Daytona Spider LHD), SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Authentic car context; camera angles intentionally NOT treated as equivalent.

## Original-derived existing source mesh edits (actual position changes, unchanged IDs)
| Part | Existing mesh ID | V/F before and after | Moved vertices | Max displacement (m) |
|---|---|---|---:|---:|
| dashboard | \`V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE\` | 1885/3584 → 1885/3584 | 317 | 0.0025133 |
| cowl | \`V8_17_ORIGINAL_GUIDED_GAUGE_COWL\` | 2594/2592 → 2594/2592 | 1945 | 0.0021272 |
| bezel | \`DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY\` | 3157/5376 → 3157/5376 | 3157 | 0.0012627 |
| spoke | \`V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0\` | 9720/17285 → 9720/17285 | 7206 | 0.0010874 |
| rim | \`V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM\` | 6144/6144 → 6144/6144 | 6144 | 0.0013403 |
| hub | \`V7_SHORT_SHAFT_AT_WHEEL_HUB\` | 224/210 → 224/210 | 140 | 0.0011156 |

**Total edited vertex positions: 18909** across **six existing P0 cockpit meshes**; no new objects/meshes, no UV or materials changes, source topology preserved. Original steering 8/8 perforations stayed open. All **107 other meshes unchanged** by signature; camera objects, source-space matrices, original steering pivot, object names and registered images preserved.

## Native model vs before/after photo QA
- A completely **separate Blender 4.5.15 process** reopened the actual R22 .blend; per-object exact signatures matched and all eight physical steering holes verified. Actual Cycles CPU render **720×480, 3 samples**, SHA256 `e10ed9d95407a815dbff9b91add4ff878c129a93b867247a215ffecca8f65884`.
- Private Cycles R21/R22 comparison `SLOTA_R21_R22_REAL_BLENDER_CYCLES_BEFORE_AFTER_PRIVATE.jpg`; max RGB difference >3 for **14894** of 345600 pixels.
- Genuine 1971 LHD Spider private three-panel `SLOTA_R22_EXACT_SPIDER_PHOTO_R21_R22_PRIVATE_COMPARE.jpg` compares real photo vs R21 vs R22; viewpoints not calibrated, **no final shape authenticity claim**.
- Private QA JSON: `SLOTA_R22_NATIVE_DASH_WHEEL_VERTEX_SCULPT_AUDIT.json`, `SLOTA_R22_INDEPENDENT_REOPEN_REAL_CYCLES.json`, `SLOTA_R22_NATIVE_BEFORE_AFTER_COMPARISON.json`. Rights-restricted PMT, photographs and scenes remain only on private N100.

## Safety/remaining gates
- Original-source existing nonmanifold topology: dashboard **184**, gauge bezel **932**, native-derived spoke **1597** edges. These pre-existing findings were **not repaired** in this R22 source-vertex-only pass.
- Original game calibrated driver-eye/FOV **NOT VERIFIED**; seven exact Daytona Spider photo views **INCOMPLETE**; official GitHub Actions hosted real private Blender **BLOCKED_INPUT_NOT_TRANSFERRED**. Local Blender QA PASS does **not** establish hosted CI or car completion.
- Queue stays `ACTIVE/PARTIAL_NEEDS_QA`. Do not advance before full quality gate/24h.
- No exterior body/tires, textures/normal/PBR, third-party GLB, OVC3/OVC/PMT conversion/output, game installation, Dino, Model2 or VR source modifications.
- AI competition: one ongoing geometric correction session, **score +0 pending separate score adjudication; no retry/rollover score duplication**.
