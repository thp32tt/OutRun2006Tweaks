# Slot A — Daytona365 original-game cockpit R10 (2026-11-08 KST)

Scope: **ONLY** `active_by_slot.A=daytona365`; Ferrari 365 GTS/4 Daytona. Ferrari F50 (slot C), Dino 246 and all other projects were not edited.

## Immutable original assets (N100 private, SHA256)
- Native OutRun 2006: `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` — `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`; read-only, no output/conversion.
- Original PMT-linked Blender import: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` — `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- Prior existing source scene R9: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v7_r9.blend` SHA256 `fd8ec518304d2b048f5652a91f6469cf655ba91f5a40f600e5b5021dcba09e6a`.
- New private R10: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v8_r10.blend` SHA256 `d18408d82e5de993f96ce882eff80e31eedf4b41468747785890e0942b2f6da9` (7495165 bytes).
- Private R10 scene/scripts/render folder: `/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/`; immutable earlier R9 retained.
- One actual photographed 1971 365 GTS/4 Spider LHD cockpit: `02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`, from N100 photographic reference library. The full seven-view matched-eye requirement is **not** satisfied; photo never uploaded publicly.

## Actual original-derived existing mesh editing

Official Blender **4.5.15 LTS** loaded the PMT-derived **R9 .blend**, sculpted only existing geometry, saved new R10 .blend, and a **separate Blender process** reopened and independently inspected the real private scene (not a primitive substitute). Native original source names maintained: `object00_group01_material012_a0` (dashboard) and `object22_group00_material000_a0` (three-spoke wheel). Source file, camera, object matrices, UV/material/image inventory and original pivot unchanged.

| Existing original-derived object | Vertices / faces | Changed positions | Max offset |
|---|---:|---:|---:|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` (dashboard) | 1885 / 3584 | 196 | 6.99712 mm |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` (brow) | 650 / 648 | 626 | 7.33553 mm |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` (bezel) | 908 / 1344 | 837 | 1.83192 mm |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` (spoke) | 9720 / 17285 | 4885 | 2.77024 mm |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` (rim) | 1536 / 1536 | 278 | 1.83146 mm |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` (hub) | 224 / 210 | 99 | 1.41942 mm |

- All **107** unrelated mesh geometry signatures unchanged. Eight physical source-derived steering wheel spoke holes independently checked as through-open.
- Original non-manifold geometry remains unresolved: dashboard **184**, gauge bezel **466**, original spoke **1597**; R10 does NOT claim topology repair or P0 complete.
- Fresh independent original-scene QA: `SLOT_A_R10_GENUINE_NATIVE_BLENDER_FRESH_REOPEN_PASS`; Cycles real-scene render R10 `SLOTA_DAYTONA_R10_AFTER_REAL_CYCLES_APPROX_EYE.png` SHA256 `788190a690426b9786642bf7cbb32b5a3d6416bb91e56db5ef35db7c0ad9d234`, 720×480, 3 samples.
- Private same-approx-camera original R9 ↔ R10 and genuine Spider photo comparison `SLOTA_R10_PRIVATE_REAL_SPIDER_PHOTO_R9_R10.jpg` SHA256 `f7c4e2ac759a2aa31743d92b5d121c3cc60bbc3fc40b521457268c4d3e59a576`; RGB absolute >3 at **11062/345600** pixels. A same-camera R9/R10 image comparison is valid, while genuine photo camera is **not** matched to game eye.
- No public/private game PMT/OVC3/OVC output, no game packaging/integration, no exteriors/tires, no new textures/PBR/normal maps, no slot C/Dino/Model2/VR branch touches.

## Still blocked / NOT complete

The GitHub-hosted **Blender 4.5.15 Actions VM does not have the confidential original .blend/source**, so **real private scene hosted Actions QA = BLOCKED_INPUT_NOT_TRANSFERRED**, not PASS. Original game driver-eye is NOT calibrated. Seven exact-car authentic matched view checks and full 24h allocation are incomplete. **Keep slot A Daytona ACTIVE, geometry_gate PARTIAL_NEEDS_QA, do not advance queue.** No retry/rollover/CI/report score credit: **+0**, no scoreboard mutation.

Nonproprietary scripts are committed, while licensed originals, production .blend and original/photo comparison renders remain private at the above N100 path.
