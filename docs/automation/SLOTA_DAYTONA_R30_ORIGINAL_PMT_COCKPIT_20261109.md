# Slot A — Ferrari Daytona R30 native-PMT-derived cockpit sculpt (2026-11-09)

**Scope:** `active_by_slot.A=daytona365` only. Existing original-game-derived editable R29 `.blend` cloned and modified in **Blender 4.5.15 LTS**. Only dashboard vent rings/slats, instrument cowl/upper dash and original-source steering three-spoke/rim/logo. No exterior car, wheel/tire (exterior), textures/normal/PBR, new GLB/car/scene, native conversion/PMT/OVC output, game or VR/Model2 changes. Slot C F50 and completed Dino 246 untouched.

## Immutable original and private input / output proof

- Read-only OutRun 2006 game native resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz`; SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Actual native-import original Blender file: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend`; SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`. Independently re-opened with Blender 4.5.15; native named objects `object00_group01_material012_a0` (13v) and `object22_group00_material000_a0` (61v).
- Previous genuine original-derivative private input R29: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v27_r29.blend`; SHA256 `8383d235ca0dbfa89f541ebe3681bbcaea6df65c57dda4fa8a7834f738253e36`.
- **New private editable** R30: `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v28_r30.blend`; SHA256 `beed6f9e1cc11706e21e361c22754ddc4ed2aba581087c66009dd08202f7a6fb`. Stored only under `/home/chatgpt-runner/work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/` on authorized N100; not public GitHub.
- Ferrari 365 GTS/4 Daytona Spider 1971 LHD authentic photo reference: `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg`; private SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`. Reference comparison qualitative; photo camera **not** registered to the original game eye.

## Verified in-place source-derived mesh geometry R29 → R30

**17 pre-existing source-derived objects physically edited, 12,528 moved vertex positions.** Object names, vertex and polygon counts, object/world transforms, cameras, steering pivots, UV and materials unchanged. Other **96** existing mesh geometric hash signatures unchanged; mesh inventory held constant.

| Source-derived existing object | Before/after V/F | Moved verts | Mesh SHA256 before → after (prefix) |
|---|---:|---:|---|
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495/2816 → 1495/2816 | 216 | `6a6185d43478` → `b7869db8c6f8` |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2053 | `62be9afcbf79` → `75ba90a3c667` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 2251 | `e8de793966f3` → `b58320cb7acc` |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 6144 | `b201d5baabc4` → `3d2739c061b8` |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material001_a0` | 4/2 → 4/2 | 4 | `889b8d55a60d` → `a6c36b1dadec` |
| `V5_3D_AIRVENT_0.080_CHROME_BEZEL` | 539/960 → 539/960 | 539 | `d08e25236042` → `27a58f83572e` |
| `V5_3D_AIRVENT_0.080_SLAT0` | 27/32 → 27/32 | 27 | `a5b6b2f6c06d` → `36de14261011` |
| `V5_3D_AIRVENT_0.080_SLAT1` | 27/32 → 27/32 | 27 | `7f7ca933811c` → `a7d063373fc0` |
| `V5_3D_AIRVENT_0.080_SLAT2` | 27/32 → 27/32 | 27 | `e86f48181881` → `53223e7515c5` |
| `V5_3D_AIRVENT_0.255_CHROME_BEZEL` | 539/960 → 539/960 | 539 | `397e8cfa40a0` → `de50b6994e22` |
| `V5_3D_AIRVENT_0.255_SLAT0` | 27/32 → 27/32 | 27 | `1d1ad52ed5b4` → `bb717ff38fd2` |
| `V5_3D_AIRVENT_0.255_SLAT1` | 27/32 → 27/32 | 27 | `c58a43c81b5f` → `c489f9bd3914` |
| `V5_3D_AIRVENT_0.255_SLAT2` | 27/32 → 27/32 | 27 | `7a2f557add36` → `42c8e8809618` |
| `V5_3D_AIRVENT_0.430_CHROME_BEZEL` | 539/960 → 539/960 | 539 | `4dfb461f5000` → `8635a006877a` |
| `V5_3D_AIRVENT_0.430_SLAT0` | 27/32 → 27/32 | 27 | `4d36887d4bbf` → `49511edb66df` |
| `V5_3D_AIRVENT_0.430_SLAT1` | 27/32 → 27/32 | 27 | `92122ffec3d3` → `164dad89d2a5` |
| `V5_3D_AIRVENT_0.430_SLAT2` | 27/32 → 27/32 | 27 | `48bfb2b85d44` → `9dd187830a33` |

All **full 64-digit per-object before/after geometry SHA256**, source inventory, UV/transform proofs and geometry deltas are in private `SLOTA_R30_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json`; no licensed private source asset stored in GitHub.

### Photo-guided adjustments

- Dashboard: existing upper shell and inherited instrument cowl molded as a subtle front lip, no fresh object created.
- Existing dashboard three elongated metal airvent bezels (`0.080/0.255/0.430`) gain physical leading edge/depth, existing nine louver blades sit slightly farther into the old vents; all other photos/meshes untouched.
- Existing source three-spoke press-formed wheel receives shallow metal-roll relief while keeping 8 authentic open holes. Original imported steering-emblem descendant is reduced in the same source plane so the badge proportions better approach the photo, steering rim section refined in place.
- **Visual QA limitation:** same approximate-eye render, not an actual game camera. Current 3 vent groups differ from some reference photographs; exact variant and geometry remain for later QA. None are automatically adjudicated as final visual accuracy.

## Actual Blender 4.5.15 verification

- Cloned R29 private `.blend`; original PMT/import/photo/R29 file SHA256 verified at run start; independent Blender 4.5.15 original imported-source open PASS.
- New R30 `.blend` saved, then **different Blender process** re-opened exact file and verified each edited vertex/face SHA, all other 96 mesh SHA signatures, full scene object/material/camera inventory, no newly added objects, UV/transform invariants, and original 8 steering perforations via physical BVH raycasts.
- Cycles image at 720 × 480 (CPU 3 samples), private `SLOTA_DAYTONA_R30_AFTER_REAL_CYCLES_APPROX_EYE.png` SHA256 `fc19665348f943fe277e180850c121e7955594c308d82a796898ccea66cfee65`.
- **Real R29/R30 side-by-side** private `SLOTA_DAYTONA_R29_R30_ACTUAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `cfeaba2d0c1c82e87651ebe1ae5e61b0a10ada8675dfd8c4a421ff759182a463`, with `11,415` / 345,600 pixels exceeding a max RGB channel delta of 3. Same approximate view only.
- Existing nonmanifold/open topology remains: upper shell 172 edges; original 3-spoke 1,597; emblem source plane 4; 3 vent bezels each 116; 9 louvers each 20. No claim of manifold repair.

## Unmet quality gates / isolation

- `status=ACTIVE`, `geometry_gate=NEEDS_REWORK`, `reference_gate=PARTIAL_NEEDS_7_VIEWS`; original game driver-eye transform **NOT CALIBRATED**, exact Spider photo 7 camera-aligned views **INCOMPLETE**; no 24h/P0 acceptance. **Do not advance slot A.**
- GitHub Actions official Blender 4.5.15 installed toolchain source/queue smoke is **NOT** a real private `.blend` test. **GitHub-hosted private scene: `BLOCKED_INPUT_NOT_TRANSFERRED`**. True licensed Blender scene was validated independently and kept private on N100; absence on runner prevents hosted real-scene PASS and vehicle COMPLETE.
- No new AI2 points for follow-up of existing Daytona P0 geometry; duplicate score for run retry/rollover and independent reopen prohibited, **score delta +0**. AI1 unaffected.

**Public non-proprietary geometry script:** `tools/car_modeling/slotA_daytona_r30_native_vent_and_wheel_badge_geometry.py`.
