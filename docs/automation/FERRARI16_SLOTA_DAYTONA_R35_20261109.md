# SLOT A Daytona R35 — native-source steering stamped-spoke taper (2026-11-09 KST)

## Scope / original-input witness

- Slot/owner: **A/daytona365**. Queue remains ACTIVE / NEEDS_REWORK. Slot C/F50 and Dino-246 untouched.
- Read-only original game asset: `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Genuine original game Blender PMT import `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`; raw mesh IDs `object00_group01_material012_a0` (13v/12f) and `object22_group00_material000_a0` (61v/31f) independently read in actual Blender 4.5.15.
- Exact 1971 Daytona Spider left-hand-drive private photo `02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Research-only, not redistributed. N100 `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv` checked; seven authenticated/matched angles remain unavailable.
- Existing source-backed input private R34 `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v32_r34.blend` SHA256 `a7496d2669e626c612e2a94686b584f28db624e9363121cf46e86c9a4dfda824`.

## Actual source geometry edit

R34 driver-eye Cycles compared to genuine LHD Spider photo. Tapered four **existing** original-derived steering stamp and bridge objects to reduce the overly blocky rim-end shapes; did not add/remove any steering object or replace the wheel. P0 dashboard and cluster meshes retained from verified R34; no other car parts edited.

| Existing native-derived object ID | Vertices / Faces before → after | Vertex coordinates moved | Local geometry SHA256 before → after (prefix) | Existing non-manifold edges |
|---|---:|---:|---|---:|
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9732/17300 → 9732/17300 | 419 | `6d1f8a89642c` → `3a8d0c6d788b` | 1601 |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 16 | `c0fe2279b378` → `e7a36d567651` | 0 |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 16 | `5397f9aa2639` → `02981d836132` | 0 |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 16 | `d6c36ab5142c` → `dc6f24aecdee` | 0 |

- Total **467 existing vertices** moved: spoke 419 + three source bridges × 16; topology counts and all object names/IDs, world transforms, UV/materials, camera/pivots retained. Other **109** mesh signatures unchanged.
- Source-native eight steering spoke through-holes verified by Blender BVH ray tests before build, after edit and after independent reopen.
- No OVC3, OVC, PMT, GLB, native resource conversion, game/VR source edits, external body, tires/wheels, or PBR/texture/normal creation.

## Private output and evidence (not checked into public GitHub)

- New editable original-derived private `.blend`: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v33_r35.blend` SHA256 `e64722b0d72fe79ade93bae0c03dc97771db585020440e85e5f7765455155c9f` (7,880,689 bytes).
- Nonproprietary Blender edit script: `tools/car_modeling/slotA_daytona_r35_original_spoke_bridge_taper.py`; local script SHA256 `e1d551e17eb45b421e5366c26060e77c5dfe35f3dc47a338dedfb484713a2574`.
- Real local Blender **4.5.15 LTS** saved actual scene; **independent new Blender process** reopened the exact R35 SHA and rendered Cycles 720×480, 3 samples. Render SHA256 `df0bb07f80ff4c690102f9ccfb3f6590d07d960b2964b541fe1bac96d3909f99`.
- Actual R34/R35 same approximate-eye Cycles before/after comparison: **2,218 / 345,600** RGB pixels differed by >3. Comparison `SLOTA_DAYTONA_R34_R35_REAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `1b837c177fb5ddcfe015608a0706712388a77f9afe85f347ef79a131818353fb`.
- Private audit: `SLOTA_R35_NATIVE_STEERING_TAPER_MESH_AUDIT.json`; QA: `SLOTA_R35_INDEPENDENT_REOPEN_CYCLES.json`.

## Gates / decision

- **PASS**: Original PMT SHA, first native import, actual mesh editing, real Blender 4.5.15 saved-private-scene / independent fresh reopen & Cycles, other source object preservation and 8 open punched holes.
- **INCOMPLETE**: actual in-game driver eye/camera calibration, seven angle-matched authentic Spider LHD photo references, existing spoke and dashboard non-manifold repairs, final visual handoff.
- **BLOCKED_INPUT_NOT_TRANSFERRED**: proprietary private `.blend` has not been transferred to a GitHub-hosted Blender 4.5.15 Actions runner. Official hosted **real-scene validation is NOT claimed** (public smoke/action scripts cannot prove production source results). User delivery of private `.blend` also remains unconfirmed.
- Remains **ACTIVE / NEEDS_REWORK**, no slot advance, no vehicle complete assertion; same ongoing P0 Daytona feature / no double-counted competition point (score change +0).
