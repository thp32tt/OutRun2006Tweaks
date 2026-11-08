# Ferrari 365 GTS/4 Daytona — Slot A R26 native-derived P0 geometry rework

Date: 2026-11-08 KST. Slot A only. Daytona365 ACTIVE / P0 NEEDS_REWORK. No car advance or completion claim.

## Protected private source provenance
- Original native OutRun game PMT: `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` SHA256 **`f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`**; remains read-only.
- Native original imported scene: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 **`92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`**; independently reopened in official Blender 4.5.15 LTS.
- Original imported named objects: `object00_group01_material012_a0` 13v/12f, `object22_group00_material000_a0` 61v/31f. Existing derivative cockpit source meshes retain name/ID ancestry, not an unrelated GLB.
- Actual R25 input `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v23_r25.blend` SHA256 `e9dd86adb27b25ea49f7eeb5335ef5b312bac180bf336a833f96d7cfe57715a5`.
- Private genuine 1971 GTS/4 Spider LHD reference photo `02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. N100 `MANIFEST.json` retains rights/source, and `COVERAGE_MATRIX_16x8.csv` has unverified views.

## Existing native-derived mesh geometry edits
Photo and real R25 Cycles comparison highlighted overlarge open gauge bezel, conspicuous bright lower dash band, and flat steel-spoke bridge. R26 physically revised existing upper dashboard/gauge cowling/bezel, original perforated wheel/spoke/rim/hub/column, its existing three short bridges and source-derived lower lip and trim. No new object/texture/material.

| Existing Blender mesh object | Before → after vertices/faces | Vertices moved | Pre geometry SHA256 | Post geometry SHA256 |
|---|---:|---:|---|---|
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495/2816 → 1495/2816 | 297 | `1ae3bf43f64223d0c725a96e9810850b8011b67ab34fa31ab739d5782586d5bf` | `05f753537502b245668aa2a579780a24cf49d023939a940fc9b791506a4ad868` |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 326 | `d1d6fa402f9ac7a513e2c41e9cd3c30d89503849b4f391aa65c6d5655d5d2de1` | `18afdc5296ccfec3d3d41a6be35838be0e1f6d63888b1be217aef343b8fd0db9` |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2176 | `d209c3c4a608c823d724a229cb6bb99638ac9141a9835c10986444660a2e8be4` | `c555cebf9dc37c395e67e92a7048502bdec593191446a4aeb0f690786e11d6d1` |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157/5376 → 3157/5376 | 2885 | `2d1007121c2ecae3b4ac1ff9fb9a7917e85e806f0f072e5147071d2a7fb94030` | `53b46ee24a9c20f375aaa766e8949e36deab13e02bb78b2578ab9ba8bec324ac` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 7515 | `ca3b49b6282eefbe2a786ee208f74517c453e646998b9c8e7a3881b589cd8a1f` | `92b10248fc244e4eaa7a6caf6f4520e4c8999253ec06372cf3dd0cc7d4dfedbf` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 6144 | `54390682fe9618e5094f82f9a4277f338e519cfc2296900c7d9a6c539c141f8c` | `547db8faca93454327825813f1ce4531b640d3e17e74f48fd3b939dbb441ec62` |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 → 224/210 | 186 | `b0ebe6fd79a28780700523d38557a614bc7ada8eae5f4807d727e22999cca084` | `3adf5dd0335e5a2c2cab2d9ffd9795eaa48b6dbed18ffbaa193787948a107362` |
| `V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES` | 100/82 → 100/82 | 85 | `1ed5c92c5d9d00d01b67415a533006a46d728ce79aaf6cecbb9db3b5198c8aa6` | `8e782252cb7208b9138e36964e4330d4c5986a4c01b1c1f964b150c141fa0829` |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 | `d332f3816840b94cdb2f06a7ec215883c71113183ebc6e4a29a23d0755cfd797` | `70b3470072bac1ba958102d10929c2e15c49d5cf6226cc2f0925844d6f06bbf5` |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 | `957a8298cc76db016ca0f3d32fb87c579c0b0172a721f4ad5e31ba401fd8cac6` | `ca6893bfaa49b5b850d54855d47834b0a409f2fbb02ab58065574d9a22279817` |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 | `03c415c24ff7fcda92dafa4fc107d26d1f76030bfa40edf0ded5b29a2e3128de` | `80db087d13134de14026eea72db5484019388941bbd4dcc004dbd23eb7ed7a98` |
| `V8_2_CONTINUOUS_LOWER_DASH_LIP` | 60/58 → 60/58 | 42 | `84df9efc0dc60684ab6edab2a38e50eeb0d3fdf5726fb9d1261316a2062267d2` | `9f9783d8ce8def488d037be61b6e5464cc2878f214e7a0e7b23df315c11dba93` |
| `V8_2_DASH_TRIM_STRIP` | 8/6 → 8/6 | 8 | `6d20cab392cdd42286c7996436c5be783a3ab46f3b254c5a22fff3f129d3378b` | `01324630e20143e89846eec021b989d83324ca25e0cbaf9b9575d4c7853a05e6` |

- Total **19724** moved source-derived vertices across **13 existing objects**; **100 other meshes** unchanged, aggregate SHA256 `5e36a1f6670632bb7d164a2e538adf7fc5636e4d615c9d7b3c623f6599617ff7`.
- No vertex/face count change or mesh topology remapping. Source object identities, world matrices, steering pivots, camera, UVs, image/material registry unchanged. Original factory wheel pierced holes all eight PASS.
- Pre-existing nonmanifold mesh defects remain and are not counted as resolved.

## Actually saved and independently verified Blender outputs
- Public non-proprietary script: `tools/car_modeling/slotA_daytona_r26_original_photo_dashboard_wheel_recess.py`, source commit `9258504605392b1d11c4ef244bf3f5d9f2907450`, Python SHA256 `78a9790da292dace5c792c025d96c504ab066ed7db74660273c448ccbb76b15b`.
- Private R26 source-derived .blend: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v24_r26.blend` SHA256 **`595b9f3676f8ba330cac3c1ee32fe8a0830a9d33cdc69b39dd25a386744279b9`**.
- Official Blender 4.5.15 LTS: original import reopened, R25 scene edited and separately saved as immutable R26, separate Blender process re-open and mesh/UV/source identity comparison PASS.
- Independent real Cycles CPU render `SLOTA_DAYTONA_R26_AFTER_REAL_CYCLES_APPROX_EYE.png` 720×480, 3 spp; SHA256 `42adadf60410b3c8885b20cb7f7fd5a666b36f24539ccaed8a82da5c86772103`.
- Identical approximate camera R25 vs R26 comparison `SLOTA_DAYTONA_R25_R26_ACTUAL_CYCLES_BEFORE_AFTER.jpg`; SHA256 `dc2e22780e30061352e21430876ce8c80c5d4a9c827c36e90e6a1df7fbb237a0`, **22443/345600** pixels differ above max RGB threshold 3.
- Private detailed receipts: `SLOTA_R26_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json` and `SLOTA_R26_FRESH_REOPEN_REAL_CYCLES.json`. Original licensed scene, render and photos remain only in private authorized storage.

## Pending gates / restrictions
- GitHub Actions hosted real proprietary original scene QA: **BLOCKED_INPUT_NOT_TRANSFERRED**. Public Blender smoke is not source-scene validation.
- True original game driver-eye: NOT CALIBRATED; authentic matching photo angle x7: INCOMPLETE; pre-existing nonmanifold: UNRESOLVED; P0 dashboard + steering acceptance and 24h quality gate: NOT PASSED.
- Slot A remains ACTIVE and `active_by_slot.A=daytona365`; preserve slot C and user-completed Dino.
- No external body/wheel/tire, new DDS/normal/PBR, new car/GLB, OVC3/OVC/PMT export/conversion, gameplay integration/packaging, Model2/VR source or other branches modified.
- Score delta +0; no duplicate award for same ongoing geometry checkpoint.
