# Ferrari 16 external cockpit models — exact-variant acquisition and quality gate (2026-11-18 KST)

## Task and non-negotiable acceptance

All sixteen cars should ultimately use **the actual named Ferrari body variant**, not the original OutRun PMT presented as an upgrade and not a newer/older Ferrari substitute. Requirements: separate detailed interior, intact UV/albedo/normal/PBR maps, reliable axle/ground fit, wheel/steering where supported, speed/RPM/gear bindings, no silent mesh decimation or texture downscale, and **actual Quest 3/OutRun gameplay visual QA** before saying "finished". Third-party rights must permit the intended private cross-game conversion; do not publicly ship mods with unsupported redistribution grants.

### Current baseline versus exactness

- Baseline private Ferrari16 package (2026-11-17 N100 manifest): `ExternalBodyCount=16`, `ExactExternalCount=13`, `DonorReworkCount=3`; Windows static Build PASS, no Quest 3 game QA.
- Existing intentional donor substitutions: 575 Superamerica slot = Ferrari 575M (200,071 triangles); 328 GTS slot = Ferrari 308/Quattrovalvole (139,216 triangles); F430 Spider slot = Scuderia Spider 16M (565,172 triangles).
- The **Testarossa Spider** identity is a separate potential mismatch: manifest source is **1987 Testarossa** GTA5 and does not prove the **Spider/convertible** variant displayed by OutRun 2006. Mark `VARIANT_UNVERIFIED` until roof/open cockpit and original reference images are matched.
- Latest high-detail V4 body assets previously verified: F355 Spider 444,977 triangles / animated speed and RPM; 512 BB 265,611 triangles / animated speed and RPM; F430 Spider exact-body candidate 77,979 triangles / animated gauges, **optional because it is far lower-triangle than 16M donor**.
- The independent live dashboard overlay exists for all sixteen, but overlay availability alone does not establish that the original model's native instrument pointers are accurate or visually aligned.

## New exact Superamerica conversion — PASS, optional only

- Source: Assetto Garage Ferrari Superamerica exact model, car ID 05/20 (https://assettocorsamods.io/cars/gt/ferrari_superamerica/). Existing privately obtained and converted GLB 4,899,840 bytes, original SHA256 `765e89af297a5823aa751c89835c1de97a75e6eac1e746dd38c17b8b629f46a4`.
- Actual source audit: 78 meshes, 30 materials, 43 embedded images; 16 normal-map materials.
- Native V4 conversion initially **BLOCKED** on one anomalous texture UV in `COCKPIT_HR_SUB0` (accessor 137, vertex 2031; `[638.5,-20721]`). The two unaffected corners had `[11.046875,-6.76171875]`, `[11.125,-8.94921875]`. Integer UV wrap-phase-preserving correction to `[11.5,-8]`; geometry/triangles/indices/normals and image content were untouched. Original source preserved. Repaired GLB SHA256 `c4536032e93fc03fe68c9c88079234aaabaa414aa63f9df277378be6ed47040a`.
- **Independent output validation PASS:** 51,444 triangles, 56,323 vertices, 78 groups, 30 materials, 7,157,035 bytes, DXT5 and PBR, header+CRC+geometry/material/texture/gpu-limit checks. SHA256 `0e902c45f1131c7438b57b515973e874efb9c014fb31bbb2030ea3ac4f68463d`. No native speed/RPM bindings yet; existing external dashboard overlay remains available.
- This exact source has **74% fewer triangles** than the current 575M donor, and real VR visuals are not verified; **not promoted to the default 16-car install**. Separate optional personal ZIP `Ferrari_575_Superamerica_Exact_OVC4_OPTIONAL_PRIVATE_20261118.zip` is 8,950,325 bytes, SHA256 `084ed6d6acca828deab00f910b5c95811f968c488c556e0c2e35a7cc294723e7`. It contains both the original and repaired GLBs; installer defaults to verify-only and requires explicit `-Install -AllowLowerDetail` and matching runtime DLL SHA. It is NOT uploaded to GitHub.
- Detailed machine-readable QA: `tools/car_importer/ferrari16_hq_batch/superamerica_exact_private_20261118.json`.

## Remaining source gaps, research verified November 18

| Car | Status | Concrete source candidates or blockers |
|---|---|---|
| Ferrari 328 GTS | **EXACT HQ SOURCE NOT ACQUIRED** | Existing 308/QV donor is NOT a 328. 88Cars3D offers a specifically named 328 GTS with modeled cabin/textures/.blend/.glb but lists **€10**, and actual downloaded mesh/license are not independently validated: https://88cars3d.com/product/ferrari-328-gts-3d-model/ . CGTrader SQUIR high-poly model appears paid: https://www.cgtrader.com/3d-models/car/sport-car/ferrari-328-gtb-gts-1985-1989 . 3D CAD Browser exact 328 GTS source requires a paid or qualifying uploads account: https://www.3dcadbrowser.com/3d-model/ferrari-328-gts-1985 . Old 2009 GTA SA ModDB 1.5MB model is not HQ and its original conversion lacked permission: https://www.moddb.com/downloads/ferrari-328gts . Sketchfab 328 GTB WIP model `cd5f7556028848e7b5d572134286a8e4` now explicitly disabled, also GTB rather than GTS. No exact free downloadable HQ full-cockpit model has been verified; do not fabricate one. |
| Ferrari 575 Superamerica | **EXACT V4 OPTIONAL, HQ DEFAULT GAP** | Exact Assetto Garage conversion technically PASS, only 51k triangles vs existing 575M donor 200k; not an automatic upgrade. Examine modern full 575/Superamerica source packs with provenance; no speculative promotion. |
| Ferrari F430 Spider | **EXACT V4 OPTIONAL, HQ DEFAULT GAP** | The 2005 Spider exact personal OVC4 is 77,979 triangles vs 16M donor 565,172; keep donor as default until better exact-body source. Nexus 2007 F430 Spider Enhanced model explicitly prohibits conversion to other games (https://www.nexusmods.com/gta5enhanced/mods/820); exclude even if superior. |
| Ferrari Testarossa Spider | **VARIANT AUDIT PENDING** | Existing GTA5 source lists generic 1987 Testarossa; original OutRun car is open Testarossa Spider. Need verify roof/door/seat geometry before marking exact. Avoid substituting a modern 2026 849 Testarossa or a roofed coupe. |

## Quality and permission policy

- Quality is not simply triangle count. Even if an exact source has fewer triangles than a donor, inspect **actual VR driver-eye rendering, cockpit facia, UVs, shading and clear roof visibility**. Until that visual QA, label optional rather than silently downranking.
- Prefer free permitted sources. Do not automatically purchase paid models, bypass subscriptions/account gates, or scrape non-downloadable files. Private conversion does not establish public redistribution rights.
- 360 Spider, 550 Barchetta and other sources previously rejected for explicit no-conversion/no-rework terms remain blocked until separately authorized; do not treat private packaging as permission to release publicly.
- Real game and Quest 3 QA remains untested for all newly integrated OVC4 variants. Keep the known working package unchanged.
- Next material work: acquire legitimate exact high-detail 328 GTS first; verify Testarossa open-top identity; then prioritize higher-quality exact Superamerica and F430 Spider. Only after source verification should static OVC4 and dashboard needle-bind tests run.

**Score handling:** previously scored F355/512/F430 Spider static conversions are never counted again; optional 575 exact source patch+new OVC4 verification is a distinct new achievement, subject to the scoreboard SSOT write.
