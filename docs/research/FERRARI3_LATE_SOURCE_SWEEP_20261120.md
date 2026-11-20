# Ferrari 3 exact high-quality source sweep — late 2026-11-20 KST

## Constraints and current baseline

This is the second 2026-11-20 source sweep after [earlier quality recheck](FERRARI3_SOURCE_QUALITY_RECHECK_20261120.md). Search primary source pages and compare against the [exact variant SSOT](FERRARI16_EXACT_VARIANT_AUDIT_20261118.md). Preserve the known-working game branch, the default 13/16 high-quality *exact* source count and optional-inclusive 16/16 exact candidate count. Do not claim a compiled, converted or Quest3-validated new vehicle.

No external model binary was successfully acquired or modified during this pass. One 5.47MB external GTAinside original 575 Superamerica ZIP was located, but download to ChatGPT local container failed, so it was **not** unzipped or technically inspected. Do not infer a mesh or material count from the download page. No third-party model was uploaded to GitHub.

## New source findings / refinements

### Ferrari F430 Spider — BehrBros high-resolution exact body, but commercial and technical caveats

- [FlatPyramid Ferrari F430 Spider](https://www.flatpyramid.com/3d-models/vehicles-3d-models/brands/ferrari/ferrari-f430-spider/) and [3DExport ferrari f430 spider](https://3dexport.com/3d-model-ferrari-f430-spider-3607) are **the same BehrBros asset**, not two independently acquired models. Author match; identical copy describing fully textured detailed interior, separate interior/exterior/roof, OBJ 3 resolutions **181,386–888,582 polygons** (with SubD/Meshsmooth); 3DS 3 resolutions **341,651–1,757,117 polygons**. Marketplaces list base/summary **151,449 polygons / 155,447 vertices**; these are not direct runtime triangle counts and subdivision levels must not be confused with native source quality.
- Live product prices at inspection (not historical predictions): **USD $109.95 on FlatPyramid**, **USD $129.95 on 3DExport**. Neither was purchased. 3DExport marks "Textured: Yes", but also "UVW mapping: No" and "Unwrapped UVs: Unknown", and has no rig or animation. **UV/normal/PBR, true dashboard mesh density and in-engine appearance remain unverified**. Ask for sample/UV evidence before any paid acquisition and check license limitations before bundling.
- 3DExport identifies vendor contact `support@behr-bros.de`; creator source attribution and game-content license need review before conversion/distribution. External sale copies not evidence of accessible legally reusable binary.
- This is the **first clearly documented high-polygon *stock normal Spider*, rather than Scuderia Spider 16M, candidate** in the current audit. Due to paid access and unverified textures it is **PAID_HQ_CANDIDATE_NO_PROMOTION**. Previous optional exact 77,979 triangles and donor default 16M 565,172 triangles remain unchanged.
- [BeamNG F430 Spider v1.1](https://www.modland.net/beamng.drive-mods/cars/f430-spider.html) remains free high-priority quality lead (445.1MB PBR animated dashboard; exact original author permission still not proven). Its webpage's customer comments mention damage-state texture problems, which do **not** prove the normal cockpit is bad; if original rights and archive access are established, assess undamaged cockpit and a texture path/material audit before any conversion. Secondary listing [VGTimes 2026-02-15](https://vgtimes.com/games/beamng.drive/files/92027-ferrari-f430-spider-v1-1-0-38-x.html) names PrivateMods author and STR1KE uploader; marketplace ModLand lists uploader Fairy Evolution. Avoid treating mirrors as an original source grant.

### 575 Superamerica — genuine scratch-origin open-roof variants, low-HQ potential

- [GTAGarage Kelvin Lee original author page](https://www.gtagarage.com/mods/show.php?id=695) is superior provenance to generic GTA-SA mirror pages. The author states his **scratch-made 575 Superamerica V2.0** includes **roof up, roof down**, tinted-window, normal- and high-spec versions and high/medium/low texture variants; historic 2005 release. Important for correct Superamerica 180° rotating-roof/open-deck variant **reference and potential partial geometry reuse** where allowed.
- Author explicitly states model and textures are his artistic property; there is no verified right to redistribute a cross-game package. [GTAinside original download listing](https://www.gtainside.com/sanandreas/cars/5652-ferrari-575-superamerica/download/) links a 5.47MB ZIP (direct archive inaccessible from this session), **not downloaded/tested**, and size is not mesh quality proof. Do not claim a high-quality new Superamerica default.
- Previous Assetto Garage exact optional 51,444 triangles with 2 native needles and 575M coupe donor 200,071 triangles still lead; roof geometry fidelity and cockpit/Quest3 visual QA remain blockers.

### 328 GTS — free HQ gap persists

- [88Cars3D live 328 GTS listing](https://88cars3d.com/product/ferrari-328-gts-3d-model/) states EUR 29, BLEND/FBX/GLB, textured dashboard, gauge details, UV-unwrapped surfaces and separate roof/body. These claims lack binary/Blender scene and normal-map validation. Purchase is unapproved.
- Web search across GTA5, Assetto Corsa, BeamNG, Sketchfab, Free3D and other 3D indexes yielded **no new independently verifiable creator-authorized, exact, textured, high-detail free 328 GTS full cockpit** above the existing donor quality gate. Some results confuse 308 GTS and 328, use printable rear half only, or request a model rather than offering the file.
- Previous private exact 328 GTS 66,391-triangle OVC4 vs 308/QV 139,216-triangle higher-geometry donor, unchanged.

## Next steps

1. Prioritize **free F430 BeamNG v1.1 original distributor/creator authorization and actual archive manifest**. Compare unique stock open-top DAE body+cockpit mesh, image dimensions/materials/normal maps, dynamic instrument needle pivots, and no-reduction GLB+OVC4 possibility. Do not run untrusted binaries.
2. Request an authorized *sample* from BehrBros if a paid route is explicitly approved later; verify the claimed 888,582 polygon variant and UVs before purchasing. Two sales listings are one model.
3. Use Kelvin Lee's 575 Superamerica open/closed roof versions as geometry-reference source if legitimately available; maintain current Assetto exact candidate unless a measurable visual/texture improvement is demonstrated. Do not silently graft low-detail geometry into the verified default.
4. Continue creator-owned free exact 328 GTS search (including driver cockpit dash). Purchase only with explicit approval.
5. Real game/HMD and cockpit gauge calibration remain necessary for every promotion.

## Score

Current GitHub AI2 scoreboard last confirmed commit `ac26156155f93f2f8c599009238889260c42901c` records **2876** cumulative. This is source-only and includes neither a new converted car nor independently verified runtime improvement; **2876 + 0 = 2876 AI2**, AI1 unchanged. Do not duplicate earlier exact 328, 575 gauge, F430 conversions or add points for discovery.
