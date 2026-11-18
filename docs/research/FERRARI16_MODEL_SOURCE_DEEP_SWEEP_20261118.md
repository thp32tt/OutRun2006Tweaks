# Ferrari16 source discovery — additional deep sweep, 2026-11-18 KST

## Scope
This is **source discovery, not another validated model installation or conversion**. Previous complete-in-package count remains 16/16 (13 exact + three donors). Newly found links do not change completed count, point score or Quest 3 QA. No third-party assets downloaded or distributed during this pass.

## Exact high-quality source candidates, scored by fit

| Priority | Intended game car | Candidate | Source and observed facts | Decision |
|---|---|---|---|---|
| P1 | Ferrari 328 GTS | [88Cars3D Ferrari 328 GTS](https://88cars3d.com/product/ferrari-328-gts-3d-model/) | Exact GTS named; website claims cockpit, textures/materials, GLB/FBX/BLEND available; €10 listed. Actual file, 3D triangle/UV/normal detail and conversion/redistribution license **not independently checked** | **PAID_CANDIDATE_NOT_ACQUIRED**; no purchase without explicit approval |
| P1 | Ferrari 328 GTS | [SQUIR Ferrari 328 GTB GTS 1985-89](https://www.cgtrader.com/3d-models/car/sport-car/ferrari-328-gtb-gts-1985-1989) | Named GTB/GTS 500,000 polygon high-poly commercial model, materials/textures; only model marketing claims validated | **PAID_CANDIDATE_NOT_ACQUIRED**; may be visually better but cannot assume fitted open roof |
| P1 | Ferrari 328 GTS | [Meshy gallery Ferrari 328 GTS](https://www.meshy.ai/posts/019fae39-bdcf-772c-b7dd-279790b89e7e) | Free 3D generation listing titled "Ferrari 328 GTS at Gallery Aaldering"; no verifiable actual download format, detailed cockpit or topology/UV/rights under model-page response | **NEEDS_SOURCE_INSPECTION**, no complete car evidence |
| P1 | Ferrari 328 GTS | [Ferrari 308 GTS @niev Sketchfab](https://sketchfab.com/3d-models/ferrari-308-gts-dacffa75e5fe46ce99fe6dd6223cb5a7) | Source is a genuine high-poly **308 GTS**, ~688,100 triangles / 403,700 vertices, not a 328. Useful photo/modeling reference for updating donor but *not exact source* | **WRONG_VARIANT**, no count increase |
| P2 | Ferrari F430 Spider | [GTR2 F430 Spider Addon v1.0](https://esport-racing.de/ferrari-f430-spider-addon/) | New candidate; scca1981's high-polygon **normal F430 Spider** converted from Test Drive Unlimited, includes GTR2 vehicle data; ~10 MB archive offered. Creator says no release without permission, and underlying TDU game content has separate IP. Static file download, exact triangle count, texture/normal and dashboard bindings not checked | **CANDIDATE_HQ_CHECK_NEEDED, NO_REUPLOAD**; compare with 565,172-triangle existing Scuderia 16M donor; conversion rights must be resolved before any public distribution |
| P2 | Ferrari F430 Spider | [2007 F430 Spider Enhanced Nexus](https://www.nexusmods.com/gta5enhanced/mods/820) | Normal Spider, potentially better visuals, but uploader explicitly disallows **conversion to other games**, redistribution and modification without permission | **REJECT** under stated terms |
| P2 | Ferrari F430 Spider | [TDU original Ferrari F430 Spider](https://www.igcd.net/vehicle.php?id=20870) | Confirms 2005 Ferrari F430 Spider is in TDU. Access only through a legitimately owned game; no third-party archive/direct model discovered | **SOURCE_REFERENCE_ONLY** |
| P3 | Ferrari 575 Superamerica | [NFSMods Ferrari 575M Superamerica](https://nfsmods.xyz/mod/691) | Exact Superamerica shape and user-reported HQ cockpit, but old NFS Shift→Carbon 2018 package 2.82 MB; does not establish triangle count / normal maps or exceed current 200,071-triangle donor. Different source owner rights | **NOT_PROMOTED_QUALITY_UNKNOWN** |
| P3 | Ferrari 575 Superamerica | [Assetto Garage Superamerica 1.1](https://assettocorsamods.io/cars/gt/ferrari_superamerica/) | Already **converted and strictly verified** into exact OVRCABH4; only 51,444 triangles, kept optional vs 200,071-triangle donor. This is **not a new find** | **ALREADY_VERIFIED_NO_DUPLICATE** |
| P3 | Ferrari 575 Superamerica | [GTA SA Superamerica v2.0](https://www.gtaall.com/gta-san-andreas/cars/15134-ferrari-575-superamerica-v20.html) | Historical original scratch model and open-top, archive years old, textures 1024²; no proof exceeds current high-poly donor | **NOT_PROMOTED** |
| P4 | Testarossa | [GTA4 Testarossa Spider Custom v1.0](https://www.gtaall.com/gta-4/cars/20516-ferrari-testarossa-spider-custom-v10.html) | Named roofless Spider, claimed detailed interior, but 2012 GTA4 archive body .wft 0.72MB + .wtd 0.86MB | **NOT_PROMOTED_OLD_LOW_PAYLOAD** |
| P4 | Testarossa | [OUTPISTON Miami Vice Testarossa Sketchfab](https://sketchfab.com/3d-models/1986-ferrari-512-testarossa-miami-vice-edition-a977e5df447343f48febe499ef4a681b) | 262,900 triangles, ~153,000 vertices; **Miami Vice coupe**, not the roofless Spider that in-game visual appears to depict; listing credits CSR2 textures | **VARIANT_UNVERIFIED**, do not count as Spider |
| P4 | Testarossa | [1987 GreenAid Testarossa GTA5](https://www.gta5-mods.com/vehicles/1987-ferrari-testarossa-add-on-extras-lods) | Working dials and 2048px textures, but regular roofed 1987 Testarossa and author acknowledges close-up texture limitations | **BODY_VARIANT_GAP**, no Spider claim |

## OutRun 2006 original-car variant nomenclature caution
- The official OutRun 2006 manual calls it **"Testarossa"** (not specifically "Spider"). [Official manual mirror](https://manuals.plus/sega/retro-out-run-2006-coast-2-coast-manual).
- The [IGCD game vehicle database](https://www.igcd.net/vehicle.php?id=25287) identifies the visually open vehicle in OutRun 2006 as **"1986 Ferrari Testarossa Spider"**, whereas other catalogues simply call it Testarossa. Therefore mark `GAME_OPEN_ROOF_SHAPE_NEEDS_VISUAL_COMPARISON`, not a legal Ferrari trim-name conclusion; capture original 0-view/1-view and compare actual roof + rear deck to candidate, then resolve.
- Preserve existing original-parts/hud and verified donor package until an exact higher-quality external source with accepted rights is available.

## Reference material for a scratch 328 GTS cockpit refinement (no binary download)
- [1988 Ferrari 328 GTS interior](https://www.carjager.com/en/buy/collection-car/ferrari-328-gts-CJVCL3110251013PWL.html)
- [1989 Ferrari 328 GTS left-hand-drive cabin](https://www.hexagonclassics.com/car/ferrari-328-gts--lhd)
- [1986 Ferrari 328 GTS exterior and multiple views](https://www.mad4wheels.com/ferrari/328-gts-1986)
These photos are *visual reference links only*; do not publicly copy copyrighted photographs into asset bundles.

## Next acquisition gates
1. Attempt to confirm exact 328 GTS free permissive high-detail full-cockpit GLB; otherwise retain **BLOCKED_EXACT_HQ** and do not purchase without permission.
2. Evaluate legal, technical conversion availability of GTR2/TDU F430 Spider **without violating original author restrictions**; if permission unobtainable, retain current body.
3. Keep searching for 575 Superamerica that preserves exact unique rotating roof and substantially exceeds the current 51k-triangle model, with true cockpit.
4. Resolve Testarossa vehicle's *actual open-roof game asset* using original game screenshot/mesh, not title alone.
5. Actual installed game/Quest 3 visuals + dashboard needle pivots + floor clearance remain required before any completed/16 status.

**No new asset imported/converted in this discovery-only pass. No AI2 score change.**
