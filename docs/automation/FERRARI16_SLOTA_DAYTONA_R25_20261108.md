# Slot A — Ferrari 365 GTS/4 Daytona R25 original-derived P0 geometry checkpoint

Date: **2026-11-08 KST**. Slot: **A**. Car: **daytona365**. Result: **ACTIVE / PARTIAL / NOT COMPLETE**.
Scope: cockpit-visible existing native-derived dashboard/gauges/steering meshes only. No original native resource mutation, no other slots, Dino, game/VR code, native format export, package, new texture, normal, PBR or external body changes.

## Original native provenance and immutable inputs

- Actual original game file (private): `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`.
- Original PMT SHA256 (pre and post): `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Original imported and separately reopened native .blend: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`.
- Original import SHA256 (pre and post): `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- Native Blender import identifiers: `object00_group01_material012_a0` (13v/12f) and `object22_group00_material000_a0` (61v/31f). Both individually verified in actual Blender 4.5.15 official release.
- Immutable R24 input: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v22_r24.blend` SHA256 `15d2aea9058ff1bf6099fd349b89e200c178e722410a51be4d41bf790a513af9`.
- Private authentic 1971 Daytona Spider LHD research photo: `02_365_GTS4_Daytona/ADD_interior_LHD.jpg`, SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Source/rights governed by private N100 `MANIFEST.json`, photo is not public. Coverage `COVERAGE_MATRIX_16x8.csv` still includes `UNTESTED_VISUAL` views; camera match not established.

## Physical geometry changes to EXISTING Blender imported source-derived objects

R25 narrows the source-derived instrument hood crown, recesses fascia and existing gauge bezels, rolls the original three-spoke sheet-metal face while guarding eight factory through-holes, adjusts the existing steering rim grip cross-section, and sculpts the original-derived hub/column transitions. These are vertex-coordinate changes in eight already existing objects, not replacement geometry or color tweaks.

| Original/source-derived object ID | Vertices/faces before → after | Vertices moved | Before mesh SHA256 | After mesh SHA256 |
|---|---:|---:|---|---|
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495/2816 → 1495/2816 | 337 | `b153f8c8d2984540f4aa954fe2082b3d2ea5b16ee6af09c561d9edc0ae676933` | `1ae3bf43f64223d0c725a96e9810850b8011b67ab34fa31ab739d5782586d5bf` |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 417 | `8a3372783cb52e0fe9b14fc60626a7d75fd070133bb0a7c5af1d01d649adeab0` | `d1d6fa402f9ac7a513e2c41e9cd3c30d89503849b4f391aa65c6d5655d5d2de1` |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2478 | `308ebcfc404dd4124109d92648a00cea6d9fc422d32afba3f3e98610290f7355` | `d209c3c4a608c823d724a229cb6bb99638ac9141a9835c10986444660a2e8be4` |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157/5376 → 3157/5376 | 2771 | `f9c188b16840e4740805c7d2c1677082384b3440f032dbbc1bf5f5f75cc065d3` | `2d1007121c2ecae3b4ac1ff9fb9a7917e85e806f0f072e5147071d2a7fb94030` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 7425 | `94055bc77d9401b32a5f178b3a46d11b449020e1eb715f1fa4d4643138a00ce4` | `ca3b49b6282eefbe2a786ee208f74517c453e646998b9c8e7a3881b589cd8a1f` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 6144 | `3d9ddc69337bffb9d33e320619b892ea16027b73ae4895c046afa4bc715a77e2` | `54390682fe9618e5094f82f9a4277f338e519cfc2296900c7d9a6c539c141f8c` |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 → 224/210 | 194 | `944f2efd5234dac1f965789ed07a85c7db7e9f630e5e25c039dfaf518774274f` | `b0ebe6fd79a28780700523d38557a614bc7ada8eae5f4807d727e22999cca084` |
| `V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES` | 100/82 → 100/82 | 87 | `48184c2fa8a2ea1ffdf056ebeaf249403a9d636aa5f114ee12eea6316eccd974` | `1ed5c92c5d9d00d01b67415a533006a46d728ce79aaf6cecbb9db3b5198c8aa6` |

Total physically moved existing vertices: **19853** across **8 existing mesh objects**. Separate source identity, world matrices, UV and materials are unchanged; **105 other mesh hashes unchanged** (audit SHA256 `3e71ed6edc1bb20c5008d5dbf4d07fbf519259eb64e426e841805dfe99dd772f`). Eight original spoke holes still open. Existing nonmanifold edges are unresolved and NOT counted as repaired.

## Actual private Blender output / independent process QA

- Public nonproprietary editing script: `tools/car_modeling/slotA_daytona_r25_original_dashboard_steering_profile.py`, source commit `7fcb47a84f4f255020e19f894bfe3b22ec47c6cf`, private script SHA256 `29fa95272add181b5f512517cb87e24e8dff79178f2d43268e201ab2d3e25b15`.
- Private immutable .blend output: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v23_r25.blend` SHA256 **`e9dd86adb27b25ea49f7eeb5335ef5b312bac180bf336a833f96d7cfe57715a5`**.
- Actual separately launched Blender **4.5.15 LTS** opened saved R25 and independently checked mesh hashes/UV/matrix, original factory spoke holes and mesh inventory.
- Real actual private Cycles CPU render (720×480, 3 spp, approximate test eye): `SLOTA_DAYTONA_R25_AFTER_REAL_CYCLES_APPROX_EYE.png`, SHA256 `569ad694fe89bd536b99476f240dbe870847684fb92986df568be03668b45dc4`.
- Real R24/R25 side-by-side: `SLOTA_DAYTONA_R24_R25_ACTUAL_CYCLES_BEFORE_AFTER.jpg`, SHA256 `767dd7b29411ec1c9ed70c2d0c5ccb92340fd5956f14676c95749b3b3982785b`, **15233** pixels changed at RGB difference >3 on same approximate camera.
- Private source geometries and results are stored only on authorized N100; public GitHub contains nonproprietary script, audit report and queue state, no native .blend or source photo.
- Individual QA receipts: `SLOTA_R25_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json` and `SLOTA_R25_FRESH_REOPEN_REAL_CYCLES.json` in private workspace.

## Gates still BLOCKED / incomplete

**GitHub Actions hosted full ORIGINAL .blend and independent real-scene render: BLOCKED_INPUT_NOT_TRANSFERRED.** Hosted Blender smoke does not have N100 licensed .blend and cannot certify it. The private scene was genuinely reopened locally on N100, not claimed to have been reopened on the hosted runner.

- Actual in-game driver eye: **NOT CALIBRATED**, test render approximate only.
- Correct 7 photograph viewpoint comparisons: **INCOMPLETE**.
- Source nonmanifold edges: **UNRESOLVED** (R25 QA receipt has independent counts).
- 24-hour P0 dashboard + steering quality gate: **NOT PASSED**; user visual approval not obtained.
- Slot A remains `daytona365 ACTIVE`; **no next-car advancement** and no `COMPLETE` claim. Slot C F50, Dino and all VR/runtime branches untouched.
- AI score change **+0** (one continued work checkpoint; no score duplicated for render/CI/retry).

