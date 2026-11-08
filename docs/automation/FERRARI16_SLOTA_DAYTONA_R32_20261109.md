# Ferrari 365 GTS/4 Daytona cockpit Slot A — R32, verified native-PMT-derived geometry

Date: 2026-11-09 KST. Target exclusively `active_by_slot["A"] = "daytona365"`. Status `ACTIVE / NEEDS_REWORK`. **NOT COMPLETE**.

## Original assets and reference provenance
- Read-only original OutRun 2006 native PMT: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`, SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Genuine initial Blender PMT import: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`, SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Actual official Blender 4.5.15 independently loaded and checked original object identities: `object00_group01_material012_a0` (13 vertices) and `object22_group00_material000_a0` (61 vertices).
- R31 immutable private source: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v29_r31.blend`, SHA256 `bade05a1c4b5fd5fd8b26d9ba0a675d18d4d2458ab95ca2283d1d5eea6b2e116`.
- Private 1971 genuine Daytona Spider LHD interior reference: `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg`, SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Its provenance and usage restrictions are in N100 `MANIFEST.json`. The `COVERAGE_MATRIX_16x8.csv` shows no dedicated photo tags for five of eight angles; reference coverage is insufficient for the seven-view acceptance gate. Image never copied into GitHub.

## Actual modified ORIGINAL-DERIVED existing Blender meshes
No geometry mesh/object was created or replaced. All six existing objects keep their exact vertex/face counts, names, UV coordinates, world transformations, visibility, mesh topology and material assignments; existing other 107 meshes remain byte-signature equivalent. Source edits affect position coordinates only.

| Source-derived existing object name | Before/after vertices | Before/after faces | Real vertices moved | Pre-existing non-manifold edges |
|---|---:|---:|---:|---:|
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157 | 5376 | 3146 | 932 |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885 | 3584 | 588 | 184 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594 | 2592 | 2207 | 0 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720 | 17285 | 136 | 1597 |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144 | 6144 | 3248 | 0 |
| `V8_21_SOURCE_LOWER_GAUGE_SHROUD` | 168 | 162 | 126 | 0 |
| **Total physical vertex position edits** | | | **9451** | |

- Authentic 3 existing gauge-metal assemblies `[1351,903,903]` vertices are retained and given shallow engraved/recessed bezel lip profile. Original gauge locations and imagery are unchanged.
- Original-derived dash pad/visor and lower instrument return receive modest relief with source silhouette anchoring.
- Factory steering source has 15 inherited connected components; the exact pre-existing **190-vertex center boss component** receives local metal-depth profile, rather than a new cylinder or substituted wheel.
- Existing 6144-vertex wheel rim profile refined; wheel animation/local transforms and eight punched factory through-holes preserved (fresh Blender BVH ray verification PASS).
- Whole-scene inventory, materials, UVs, cameras, original object identities and source-to-edit transforms unchanged. No texture/normal/PBR operations, no exterior/bodies/wheels/tires, no other cars or code branches.

## Genuine Blender 4.5.15 results, private authoritative scene
- Public non-proprietary source edit script: `tools/car_modeling/slotA_daytona_r32_original_gauge_bezel_hub_relief.py`.
- **Private editable new result**: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v30_r32.blend`.
- Exact immutable output SHA256: `0caafbf7c242ef539ead91c280f147a1d5893802355f8a9c9664a31761d6bc35`.
- Original load, R31 source load, R32 save, independent new process R32 reopen, all six changed mesh fingerprints and unchanged 107 mesh signatures, source eight through-holes, topology, source checksums: **PASS**.
- Fresh actual CPU Cycles 720×480 3 samples: `SLOTA_DAYTONA_R32_AFTER_REAL_CYCLES_APPROX_EYE.png`, SHA256 `6363a42d801b9a51bab3bc8b7a98f54c3ed2f1dd8cf8b334f720b33430a7df21`.
- Real R31/R32 pair, identical approximate camera/settings: `SLOTA_DAYTONA_R31_R32_REAL_CYCLES_BEFORE_AFTER.jpg`; SHA256 `1830968bb8aeeb0793e33d736afe2da907fc2be97d7ce690aba507cbade12834`. **11,840 / 345,600** image pixels have RGB max-channel delta > 3. This is actual source-model rendered evidence, not an imagined concept or independent calibrated photo match.
- Per-object signed before/after geometry fingerprints and counts: private `SLOTA_R32_ACTUAL_SOURCE_GAUGE_HUB_AUDIT.json`; separate verification: `SLOTA_R32_INDEPENDENT_REOPEN_CYCLES.json`.

## Remaining hard quality gates (do not mark complete)
1. **GitHub Actions hosted REAL private original .blend audit = BLOCKED_INPUT_NOT_TRANSFERRED**. Public script/Blender smoke does NOT equal private licensed Daytona scene hosted render. Original files must not be pushed to public GitHub.
2. Exact original in-game eye camera has **NOT** been calibrated. Seven authentic matching Daytona Spider photo angles are **INCOMPLETE**. One private Spider LHD photo was a qualitative guide only, not proof of registered multi-angle fidelity.
3. Original-derived pre-existing non-manifold edges (bezel 932, dashboard 184, spoke 1597) remain; no new topology defects from R32, but full watertight/geometry acceptance is not proven.
4. Vehicle's dedicated 24h phase / P0 human review must pass before moving to any other car; **slot A remains Daytona ACTIVE NEEDS_REWORK**, next car still locked.
5. This is a continuation of the already scored Daytona P0 work. **AI score +0**, no repeat CI/rerun/rollover score credit. No original native writes, GLB or OVC3/OVC/PMT conversion/export, game/Quest/VR/Model2/Dino/slot C/exterior/texture operations.
