# Ferrari 365 GTS/4 Daytona — Slot A R24 original-derived cockpit-only source rework

Date: 2026-11-08 KST. Slot: **A**. Vehicle: **daytona365**, status **ACTIVE / P0 PARTIAL**. Original PMT, import and previous saved scene were freshly hash-verified on N100 before editing. No other vehicle selected.

## Protected original provenance

| Private artifact | SHA256 |
|---|---|
| Read-only native game `rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` | `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe` |
| Verified native import `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` | `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3` |
| Immutable input `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v21_r23.blend` | `d88a2e3797a6e6867dd8354b004bb89f76a76d0ba42a17a88e76184f2fce0c70` |
| **New immutable output `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v22_r24.blend`** | **`15d2aea9058ff1bf6099fd349b89e200c178e722410a51be4d41bf790a513af9`** |

Blender source identities independently read from actual original imported scene: `object00_group01_material012_a0` (13 vertices, 12 faces), `object22_group00_material000_a0` (61 vertices, 31 faces). The 2006 PMT and native imported scene remained unchanged. Private exact 1971 Spider LHD photograph `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`; `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv` were checked. Photograph is private/rights-controlled and NOT uploaded to public GitHub.

## Actual original-derived source geometry edited in place (R23 → R24)

Driver-eye visual and real-source raycast identified long overly bright lower dashboard band from two existing meshes: `V8_2_CONTINUOUS_LOWER_DASH_LIP` and `V8_2_DASH_TRIM_STRIP`. R24 recessed and reduced their protruding geometry while reshaping the shallow instrument eyebrow, gauge bezel, dash crown, original three-spoke pressing, grip cross-section, hub and column. No object, UV, material or texture added. Still a partial visual improvement, not a claim that the authentic instrument silhouette and lower band are fully solved.

| Existing original-derived object | Before and after vertices/faces | Position-edited vertices |
|---|---|---:|
| `V5_DASHBOARD_CONTINUOUS_ROUNDED_UPPER_SHELL` | 1495/2816 → 1495/2816 | 525 |
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 → 1885/3584 | 618 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 2594/2592 → 2594/2592 | 2178 |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 3157/5376 → 3157/5376 | 3157 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 → 9720/17285 | 7830 |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 6144/6144 → 6144/6144 | 6144 |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 → 224/210 | 149 |
| `V7_CORRECTED_DARK_COLUMN_BELOW_GAUGES` | 100/82 → 100/82 | 87 |
| `V7_3_LEFT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 |
| `V7_3_RIGHT_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 |
| `V7_3_LOWER_SHORT_CHROME_SPOKE_BRIDGE` | 20/18 → 20/18 | 20 |
| `V8_2_CONTINUOUS_LOWER_DASH_LIP` | 60/58 → 60/58 | 30 |
| `V8_2_DASH_TRIM_STRIP` | 8/6 → 8/6 | 8 |

Total **20,786 real original-derived vertices repositioned across 13 EXISTING meshes**. Per-object before/after mesh SHA256, matrices, UV signatures and full source audit in N100 private `SLOTA_R24_SOURCE_DASH_WHEEL_COLUMN_AUDIT.json`. Other **100 mesh signatures unchanged**. All eight original wheel-spoke punched through-holes independently checked by BVH pre-edit and after fresh reopen.

## Validation and private-only output

- Official Blender **4.5.15 LTS** loaded original native-derived R23 and saved immutable R24 7,863,852-byte .blend; separately launched a fresh Blender process for R24 reopen.
- Real private Blender Cycles CPU image `SLOTA_DAYTONA_R24_AFTER_REAL_CYCLES_APPROX_EYE.png`, 720×480, 3 spp, SHA256 **`9a9039e7403579a0459ad4e9c177500e58b415c546a83b91e7101d9dd62f7598`**.
- Same **approximate and NOT in-game calibrated camera** R23 vs R24 shows **29,337/345,600 pixels** with per-channel max RGB difference >3. Side-by-side image `SLOTA_DAYTONA_R23_R24_ACTUAL_CYCLES_BEFORE_AFTER.jpg` SHA256 `ec47fb18913550b6b4e6485ddcc426851d976778905fab87e96fc25a388fa086`.
- All original object matrices/steering pivots, camera identities, UV content, material and image registries kept unchanged.
- Existing source nonmanifold edges **remain**: upper 172, fascia 184, bezel 932, three-spoke 1597 (no repair claimed).
- Private QA receipt `SLOTA_R24_FRESH_REOPEN_REAL_CYCLES.json`. All private outputs live only in `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/`, not a public repository.
- Public non-proprietary modeling script: `tools/car_modeling/slotA_daytona_r24_original_dashboard_steering_lower_lip.py`, source commit `d6af3dfb40e74b1761e44862e7cb654b54c55356`. Source SHA256 `a4bb3ec1d7efbcd4f421398724dfacf7027c05fcf21eb12c1520a2f29356e062`.

## Mandatory incomplete gates

**BLOCKED_INPUT_NOT_TRANSFERRED** for GitHub-hosted real proprietary original .blend QA: a workflow smoke job cannot substitute for the private original scene. No false claim of hosted real model validation. Exact original game driver-eye camera calibration, 7 correctly matched Spider views (N100 coverage incomplete), authentic P0 acceptance and the 24h quality window remain **INCOMPLETE**. Stay ACTIVE, do not advance to another vehicle.

No new car/GLB substitute, external body/wheel/tire editing, new DDS/normal/PBR/material work, native OVC3/OVC/PMT output/conversion, game packaging/testing, VR/Model2/Dino or other slot changes. Source assets read-only. No retry, render or checkpoint score credit. **AI score delta +0**, no scoreboard write.
