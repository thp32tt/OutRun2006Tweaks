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
| Ferrari 328 GTS | **EXACT V4 OPTIONAL, HQ DEFAULT GAP** | 2026-11-19: the old ModDB exact 328 GTS GTA SA source was privately acquired and fully inspected rather than assumed unusable. After DFF/TXD import, damage/VLO/collision cleanup, four-wheel restoration, exact 2.350 m wheelbase alignment and ground fit, OVRCABH4 conversion independently PASSed at 66,391 triangles / 55,533 vertices / 44 groups / 12 materials, SHA256 `a4608bd0d9c8a4743cddd17a0306276fb10aa24628c5817ce0e2bced67058dd1`. It remains optional/private because redistribution permission is unverified and it is lower-detail than the 139,216-triangle 308/QV donor. Paid HQ candidates (88Cars3D, SQUIR/CGTrader, 3D CAD Browser) are still not automatically purchased. |
| Ferrari 575 Superamerica | **EXACT V4 OPTIONAL, HQ DEFAULT GAP** | Exact Assetto Garage conversion technically PASS, only 51k triangles vs existing 575M donor 200k; not an automatic upgrade. Examine modern full 575/Superamerica source packs with provenance; no speculative promotion. |
| Ferrari F430 Spider | **EXACT V4 OPTIONAL, HQ DEFAULT GAP** | The 2005 Spider exact personal OVC4 is 77,979 triangles vs 16M donor 565,172; keep donor as default until better exact-body source. Nexus 2007 F430 Spider Enhanced model explicitly prohibits conversion to other games (https://www.nexusmods.com/gta5enhanced/mods/820); exclude even if superior. |
| Ferrari Testarossa Spider | **VARIANT AUDIT PENDING** | Existing GTA5 source lists generic 1987 Testarossa; original OutRun car is open Testarossa Spider. Need verify roof/door/seat geometry before marking exact. Avoid substituting a modern 2026 849 Testarossa or a roofed coupe. |

## 2026-11-19 remaining-three source sweep and 328 exact OVC4

- New detailed report: [FERRARI3_REMAINING_EXACT_SWEEP_20261119.md](FERRARI3_REMAINING_EXACT_SWEEP_20261119.md).
- Machine evidence: `tools/car_importer/ferrari16_hq_batch/remaining3_exact_sweep_20261119.json`.
- 328 GTS now has a verified exact private OVC4 candidate: 66,391 triangles, output SHA256 `a4608bd0d9c8a4743cddd17a0306276fb10aa24628c5817ce0e2bced67058dd1`. It is **not** promoted over the 139,216-triangle donor until an exact source also clears the no-quality-regression and Quest3 visual gates.
- A newly downloaded NFS Shift-origin 575 Superamerica was parsed with Carbon-specific 144-byte mesh entries after rejecting an incorrect generic-parser overcount. The exact candidate does not exceed the already retained 51,444-triangle Assetto Garage exact OVC4 and therefore is not adopted.
- A TDU-origin GTR2 F430 Spider source imported 29 GMT meshes successfully but remains below the already retained 77,979-triangle exact OVC4 and far below the 565,172-triangle 16M donor; no replacement.
- Current accounting: **16/16 exact external private candidates exist if optional exact sources are counted (13-car exact package + optional exact 575 Superamerica + optional exact F430 Spider + new optional exact 328 GTS), but the default high-quality exact package remains 13/16**. This distinction prevents a lower-detail exact model from silently replacing a stronger donor.
- No new third-party model binary was committed to GitHub and no new Quest3 runtime PASS is claimed.

## Quality and permission policy

- Quality is not simply triangle count. Even if an exact source has fewer triangles than a donor, inspect **actual VR driver-eye rendering, cockpit facia, UVs, shading and clear roof visibility**. Until that visual QA, label optional rather than silently downranking.
- Prefer free permitted sources. Do not automatically purchase paid models, bypass subscriptions/account gates, or scrape non-downloadable files. Private conversion does not establish public redistribution rights.
- 360 Spider, 550 Barchetta and other sources previously rejected for explicit no-conversion/no-rework terms remain blocked until separately authorized; do not treat private packaging as permission to release publicly.
- Real game and Quest 3 QA remains untested for all newly integrated OVC4 variants. Keep the known working package unchanged.
- Next material work: acquire legitimate exact high-detail 328 GTS first; verify Testarossa open-top identity; then prioritize higher-quality exact Superamerica and F430 Spider. Only after source verification should static OVC4 and dashboard needle-bind tests run.

**Score handling:** previously scored F355/512/F430 Spider static conversions are never counted again; optional 575 exact source patch+new OVC4 verification is a distinct new achievement, subject to the scoreboard SSOT write.

## Additional source discovery (2026-11-18, no new conversion)

See [`FERRARI16_MODEL_SOURCE_DEEP_SWEEP_20261118.md`](FERRARI16_MODEL_SOURCE_DEEP_SWEEP_20261118.md) for the expanded Ferrari 328 GTS / Test Drive Unlimited-based GTR2 F430 Spider / 575 Superamerica / classic Testarossa Spider source audit, copyright gates, and actual quality limitations. Discovery alone is **not** a new tested car or AI2 scoring event; all previous 16-car and Quest3 QA counts are unchanged.

## 13 exact-source private test package (2026-11-18)

Read [FERRARI13_PRIVATE_QA_AND_DEPLOY_20261118.md](FERRARI13_PRIVATE_QA_AND_DEPLOY_20261118.md) first for the current 13/13 real OVC+overlay SHA/CRC/DDS/PBR static QA PASS, the 600,257,798-byte private standalone test ZIP and Windows PowerShell install/backup/rollback CI run 44302240641 SUCCESS. This is **not** a Quest 3 in-game visual PASS; F40/288 GTO normal maps missing and Testarossa Spider body variant unconfirmed. Only 13 sources are included; donor models remain untouched. The score for this one package is to be counted once.

## Operational status 2026-11-19 — 13-car one-click diagnostic repackage

**Current Ferrari13 test link and white-screen triage:** [FERRARI13_WHITESCREEN_FOLDER_READY_DIAGNOSTIC_20261119.md](FERRARI13_WHITESCREEN_FOLDER_READY_DIAGNOSTIC_20261119.md). Game-root extract + `START-FERRARI13-VR.cmd`, logging ON, normal fallback allowed, and separate `COLLECT-FERRARI13-LOGS.cmd`. Real uploaded later-session watchdog and host logs have **0 stereo frames** / directReady=0 / game-client-missing; do not call 13/13 Quest 3 gameplay complete until physical re-test. This is a retry of launcher correctness, **no duplicate AI2 score**.

## 2026-11-19 physical white-screen BLOCKER (new uploaded real game logs)

Before any Ferrari13 Quest3 QA claims, see [FERRARI13_WHITESCREEN_MENU_RECOVERY_MATCHEDHOST_20261119.md](FERRARI13_WHITESCREEN_MENU_RECOVERY_MATCHEDHOST_20261119.md). Original user log proved DLL loaded and menu Present >1024, camera 9/playerCar=0, stereo game frames=0, directReady=0, old host built against older revision. New fully bundled private D3D9-classic recovery test and optional 461 KB matched-host-only patch supplied, **not yet verified on the actual Quest 3**. The 13 exact-source model bytes have not changed and all prior 13/13 static QA remains, but *hardware VR completed=0* until physical proof. Do not score the same corrective work twice.


## 2026-11-19 later cross-check — CadNav F430 MAX source quality gate

See [FERRARI3_CADNAV_F430_MAX_IMPORT_QA_20261119.md](FERRARI3_CADNAV_F430_MAX_IMPORT_QA_20261119.md). An additional actual Ferrari F430 F1 Spider-labelled 3ds Max source was privately downloaded, imported with Blender 5.2.4 and exported as GLB; imported geometry contained 127 meshes / 115,091 mesh polygons, only one material and **zero texture images**, and the independent Blender render showed misaligned wheel/body components and elongated stray meshes. An alternate matrix import did not correct the misfit. The 527,622 advertised polygon count was not recovered by the importer. **Conversion technically succeeded, visual quality gate FAILED; no OVC4/default replacement, no Quest 3 PASS.** Keep 16/16 optional-inclusive exact-source candidates and 13/16 default high-quality exact slots unchanged. Source-only follow-up adds **0 AI2 points**.
