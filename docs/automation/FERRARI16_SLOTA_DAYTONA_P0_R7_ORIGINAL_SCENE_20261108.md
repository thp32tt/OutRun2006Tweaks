# Ferrari16 Slot A — original-native Daytona P0 instrument binnacle / steering r7

Date: **2026-11-08 KST**. Owner: AI2 Slot A only. This is **not** vehicle completion, game export, new car or texture work.

## SSOT/input authorization (private N100)

- GitHub queue `active_by_slot.A=daytona365`; slot C F50 and completed Dino246 not modified. 24h minimum allocation starts **2026-11-08 04:13:41Z**, ends **2026-11-09 04:13:41Z**; P0 and exact-camera QA still require work afterward.
- Actual immutable native OutRun 2006 source: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe` (read-only). Verified original imported Blender `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Original object names `object00_group01_material012_a0` (13v/12f dash reference), `object22_group00_material000_a0` (61v/31f original wheel).
- Source private editable r6 scene `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v4_r6.blend`, SHA256 `cb220cd75eb09c84fe722a14b5d4bc268a8cf1d9af23c77aba56a97c38b19ea9`, source-backed `V5_` original-derived objects and original import verified before edits. No unrelated GLB.
- Exact 1971 Daytona GTS/4 Spider LHD photograph in private library `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg`, SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`; the `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv` document missing qualified images for other 7-view QA requirements. No GTB coupe photo is silently promoted to Spider evidence.

## New geometry actually modified (Blender 4.5.15 LTS)

Output **private editable original-derived**:
`/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v5_r7.blend`

SHA256 **`a66f156b5f30971263fd1dd623075d275e15c0e73da0e48a94ccf38bbdf645fa`**, size **7,489,657 bytes**.

| Preserved existing source-linked object | Before → After vertex/face | Changed vertices | Maximum displacement |
| --- | --- | ---: | ---: |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 456 | 12.703 mm |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 650/648 → 650/648 | 463 | 10.655 mm |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 1091 | 2.500 mm |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 1536/1536 → 1536/1536 | 256 | 2.200 mm |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 → 224/210 | 64 | 1.090 mm |

**2,330 existing original-derived vertices moved.** The actual source-grid dashboard instrument field is recessed and the prior original-guided upper cowl is rounded and extended; lower 3-spoke steel press contour, the existing rim grip and original shaft collar are reshaped, not replaced. Original object names/transform matrices, original camera, UV/material/packed images unchanged; 108 unrelated mesh objects have identical geometry signatures. Eight real existing steering spoke holes were rechecked in the fresh Blender scene with center-ray open/surrounding-metal hit. Exact signatures, input and output SHA, world matrix and counts saved in private `SLOT_A_DAYTONA_P0_R7_ORIGINAL_BINNACLE_SPOKE.json`.

## Actual verified original-scene pipeline

- Source editing script: `tools/car_modeling/slotA_daytona_r7_native_binnacle_steering_sculpt.py`; actual source commit `9185f7b7e208da3b056a43693d56468d910eef09`.
- Independent fresh-process validator `tools/car_modeling/slotA_daytona_r7_independent_native_scene_verify.py` commit `fbc5599b3da6620e413e894b365621e26e24a20d`: official 4.5.15 LTS **PASS** opening exact private r7 .blend, all 5 changed source-linked objects, 108 untouched meshes, source original PMT, original-import SHA, photo SHA, and eight through-hole rays. This is actual original-scene validation executed privately on N100, NOT a GitHub-hosted production scene audit.
- Actual CPU Cycles comparison script `tools/car_modeling/slotA_daytona_r7_real_scene_cycles_compare.py` commit `e2305f29eb62bdece6d3ba2e57d35b24e4508622`; rendered source r6 and candidate r7 in separate Blender processes, identical approximate camera `(-.35,-.92,1.055)`, target `(-.24,.19,.797)`, lens 28mm, resolution **720×480**, 3 samples. Before image SHA256 `abfee50e4aaf74c692a381c6ba2fa534a6a6aa4134fac36c1c713dfa50837f99`; after image SHA256 `9a53e3f1d6c5ad743c49ca5b2875885c3812f25376c2620fd2f39f257eb7db4d`.
- Private three-panel actual Spider photo/source r6/new r7 render `SLOTA_DAYTONA_R7_REAL_SPIDER_PHOTO_R6_R7_PRIVATE.jpg`, SHA256 `338ca812a9b6f9a041abccfe33d12f5d2157e7c487d308b47a551fa29c5b06f0`. Actual render differences are small at wide-angle view (~0.975% RGB pixels changing by 8+). This supports actual mesh changes, **not** exact-photo dimensional accuracy.
- GitHub Actions for exact source-bearing SHAs: `42452462309` source, `42452503075` independent validator, `42452535175` renderer, all SUCCESS for queue/source guards + **Blender toolchain smoke**. These hosted runs do **NOT** contain private .blend, so hosted production-scene QA stays `BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`.

## Incomplete QA and invariants

- Original-game driver-eye camera and vehicle steering pivot animation alignment **NOT verified**; same approximate comparison view only. Seven qualified Spider camera/photo matched views **INCOMPLETE**.
- Non-manifold edge findings persist: source-derived steering spoke 1597, dashboard 184; cowl 0, steering rim 0, hub 0. Visual comparison shows the cowl/dashboard surfaces and gauges still differ from the photo, so **P0 dashboard and steering remain PARTIAL_NEEDS_QA**.
- **No new vehicle, GLB, exterior body/tire/exterior wheel, textures, normal map, PBR, PMT/OVC/OVC3 conversion/output, game build, mod installation, runtime/VR source, Model2, Dino or slot-C modification.** Original PMT intact. Private proprietary .blend and photo were not committed to public GitHub.
- Slot A must remain `ACTIVE` on Daytona until full 24h, real source photo QA and driver-eye/P0 gates PASS. Existing Daytona original P0 source-modeling achievement was already scored; this is continuation of the *same* feature. **AI2 score delta: +0**; repeated CI/renders/checkpoint docs are not new achievements.
