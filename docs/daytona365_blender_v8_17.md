# Ferrari 365 GTS/4 Daytona — Blender v8.17 gauge cowl / original packed PBR

Date: 2026-11-08 KST. Private source: immutable v8.16 `d0f3406886262359e9c079ee7eeb122d9a9ac5739d5ffb9148055c9422ee77da` (actual official Blender).
Production branch: `feature/daytona365-blender-v8-20261108`.

## Implemented real geometry and materials

- `tools/blender_daytona365_v8_17_cowl_pbr_normals.py`: 408 actual existing dashboard upper-shell vertices reshaped with at most 8mm uplift; new *solid, closed* gauge cowl 650 vertices/648 faces, physically formed front lip and underside; original 65-point instrument cowl trim curve follows the new edge.
- New object extends x [-0.635,-0.05], y [0.141,0.229], z [0.9125,0.951] meters within the incumbent cockpit envelope. NOT a recovered exact PMT topology; visual original PMT comparison constrains the concept, and no actual original game PMT data are released.
- Existing packed BlackLeather BaseColor, tangent Normal, ORM green roughness, HeightOffline retained in a cloned dark-charcoal dashboard PBR with metallic=0, roughness [.68,.86] and restrained bump. Actual 256x256 analytically generated extra tangent normal was packed into the .blend SHA256 `64ab58cee82f81943de28f36d6e22a442de032740c6d3e22c9d1f7ad2fb428c7`. Existing original 20-vertex gauge atlas, 908-vertex metal bezels, 70-vertex switchbank, source chrome shifter, 4 seat shells, previous steering and controls preserve mesh hashes.

## Verified actual scene and actual render

- Saved Blender 4.5.15 LTS, private `Daytona365_Cockpit_Blender_PBR_v8_17.blend` SHA256 **`fcbe1755599de7a67af43bf7497f8889a756cb5e529efc031ccb1279e3abf1c7`**, 6,825,251 bytes. New independent Blender process reopened: **PASS**, 107 mesh/98 curve objects, 650/648 cowl topology, original packed PBR texture nodes still linked.
- Source-camera Cycles preview at **480x320, 4 spp, two CPU threads**, Blender 4.5.15, denoised, exposure -0.52: [actual v8.17 render](images/daytona365-v8/Daytona365_v8_17_ACTUAL_CYCLES_PREVIEW.png), SHA256 `159e680abaf129c643fded682fc6c879475e487a306ecbee74aa77c4df3b6808`.
- Real Cycles contact sheet [PMT original / v8.16 / v8.17](images/daytona365-v8/Daytona365_ORIGINAL_vs_V8_16_V8_17_ACTUAL_CYCLES_COMPARE.png), SHA256 `a656898b5b15221abadedb1260f61ac7513e0a471def476ec6fd9ff4aa451927`. Original PMT uses 960x640/10 spp resampled to 480x320; candidate images use 480x320/4 spp; **photometric and sample equivalence not established**.
- Static `tools/test_daytona365_v8_17_source_contract.py` checks 20 source guards; CI is source-only. Real scene/render verification was performed separately. `RENDER_VALIDATION=PREVIEW_ONLY`, `MATCHED_FULL_RESOLUTION/OVC/GAME/QUEST3=UNTESTED`.

Private editable .blend and original PMT/OVC/DDS/EXE never uploaded, and no live VR/game branch or Model2 branch modified. Next: source-original center switchbank surround and dash-to-door transition.
