# Ferrari 365 GTS/4 Daytona — Slot A, R31 original-source steering junction geometry

Date (KST): 2026-11-09. Scope: Slot A only, active car `daytona365`.
Status: **ACTIVE / NEEDS_REWORK**, **not COMPLETE**. No car-advance, score delta +0.

## Authenticated source; originals never modified
- Read-only original OutRun 2006 resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`; SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Initial independently loaded genuine PMT import: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`; SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Original object IDs checked in official Blender 4.5.15: `object00_group01_material012_a0` (13 vertices), `object22_group00_material000_a0` (61 vertices).
- Private existing editable input: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v28_r30.blend`; SHA256 `beed6f9e1cc11706e21e361c22754ddc4ed2aba581087c66009dd08202f7a6fb`.
- Correct-variant Spider LHD qualitative reference: `02_365_GTS4_Daytona/ADD_interior_LHD.jpg`; SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Private rights; never republish or treat as exact registered game-eye measurement.
- N100 `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv` checked. Daytona has no dedicated tags for driver-eye, shifter, seats, door, windshield; 7-angle authenticity QA remains incomplete.

## Actual Blender in-place edits (before and after are ORIGINAL-DERIVED mesh IDs)
Each source object's polygon count, vertex count, transforms, material slots, UV signature and visibility are preserved. Genuine position edits performed, not substitute geometry or color changes.

| Existing mesh | Vertices/faces (before = after) | Vertices physically moved | Pre-existing non-manifold edges |
|---|---:|---:|---:|
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495 / 2816 | 129 | 172 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594 / 2592 | 2207 | 0 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720 / 17285 | 859 | 1597 |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 | 0 |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 | 0 |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20 / 18 | 20 | 0 |

**Total: 3,255 moved original/source-derived vertices, six edited meshes, 107 untouched other source-backed mesh geometry signatures.**
The three existing stamped bridge pieces now have broad metal surfaces extending to the existing steering rim, instead of narrow tube-like ends; the native-source perforated three-spoke steel plate receives minor local joint adjustment without filling or reconstructing its openings. Dashboard upper and original-derived gauge visor receive modest contour refinement. No new object, material, texture, normal/PBR map, GLB or other vehicle.

## Private deliverables and actual proof
- Public geometry editing script (no licensed game resource): `tools/car_modeling/slotA_daytona_r31_original_spoke_bridge_stamping.py`.
- Private editable R31 file: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v29_r31.blend`; SHA256 `bade05a1c4b5fd5fd8b26d9ba0a675d18d4d2458ab95ca2283d1d5eea6b2e116`.
- Private object-level before/after SHA+geometry audit: `SLOTA_R31_SOURCE_BRIDGE_DASH_COWL_AUDIT.json`.
- Official Blender **4.5.15** real private source import load, build/save, **separate-process fresh reopen**, verification and 720×480 3spp CPU Cycles render: PASS on N100 private licensed scene. New image `SLOTA_DAYTONA_R31_AFTER_REAL_CYCLES_APPROX_EYE.png`; SHA256 `7dedbea484a569ed556b918a9a3b4b9f2833bd30d7547e68a948d3caed71cd2f`.
- Actual R30/R31 side-by-side render: `SLOTA_DAYTONA_R30_R31_ACTUAL_CYCLES_BEFORE_AFTER.jpg`; SHA256 `35726106d0609ce96a5234924286fad82903825aa761ca7f015b00e2c0eee1ec`. 5,089 of 345,600 pixel locations differ by >3 RGB levels using identical approximate-eye camera/exposure/render settings.
- All 8 factory steering source holes pass independent fresh-open BVH through-ray validation. Other 107 mesh signatures unchanged. No original game files written. No OVC3, OVC or PMT output; no game package, VR, exterior body/wheels, Dino or slot C modification.

## Blocks/quality gate
- **GitHub Actions hosted genuine scene audit: BLOCKED_INPUT_NOT_TRANSFERRED**. The proprietary private `.blend` was not uploaded to the hosted GitHub runner. Workflow's optional default smoke validates Blender/tooling only and cannot be cited as real original Daytona audit.
- Original OutRun in-game driver-eye camera still not calibrated against image; seven independent authentic Spider photo-view matches incomplete. Pre-existing non-manifold topology remains (not made worse). P0 dashboard/wheel still needs human eye-registered approval, and dedicated 24h phase is not complete.
- Vehicle stays Slot A `daytona365`, `ACTIVE/NEEDS_REWORK`. New material is continuation of existing Daytona P0 work: **AI +0**, no duplicate score.
