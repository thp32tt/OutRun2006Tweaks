# Ferrari remaining 3 exact-model sweep and private conversion — 2026-11-19 KST

## Result

The three unresolved exact-variant slots remain:

- Ferrari 328 GTS
- Ferrari 575 Superamerica
- Ferrari F430 Spider

This pass adds a **new exact Ferrari 328 GTS private OVC4 candidate**. The existing high-detail donor remains the default because the exact model is lower-detail. New 575 Superamerica and F430 Spider sources were also downloaded and structurally inspected, but neither is an upgrade over the already retained exact/private candidate or current donor.

No third-party vehicle binary is committed to GitHub.

## Ferrari 328 GTS — new exact private candidate PASS

Source archive:
- ModDB Ferrari 328 GTS GTA San Andreas conversion
- Archive SHA256: `86bd3f8444638ab6135853a88a90409b8b6b43c704bc474ab9978fbd8d11e491`
- DFF SHA256: `c62702405f4fcac84f833c7a18eea083fc8b70fab05a8dce23e2a8fdf8a17951`
- TXD SHA256: `65d4897471609aea7c21e9525de0d2082aba95cc9a6a78e82ce7e2e31bc14b26`
- Credits in archive: Jumper original model; Boobel/Sputn1k GTA SA conversion.
- Rights status: **PRIVATE PERSONAL CONVERSION ONLY / NO REDISTRIBUTION**. A conversion/redistribution grant was not independently verified.

Conversion:
- DragonFF imported the DFF/TXD into Blender 5.2.4 LTS.
- Removed damage duplicates, VLO, collision/shadow meshes and Blender default objects.
- The source contained one wheel mesh attached to the RF wheel dummy; the same source wheel mesh was instanced to LF/LB/RB so all four wheel positions are present.
- Wheel dummy centres were measured before scaling. Source wheelbase: 2.670107424 m.
- Uniform scale: 0.8801144023828934, targeting Ferrari 328 GTS wheelbase 2.350 m.
- Longitudinal axle midpoint was centered and the lowest retained visible mesh was grounded at 0 m.
- Retained aligned GLB: 3,409,652 bytes, SHA256 `f3f4b19ec9750f85ac1a46fc0a9b950c9bb65521028b53d4ab052954ab07d9c8`.
- Retained Blender checkpoint SHA256: `83c705c0ec7e8d821ae30d21df31dcdd1ac4b04a9aef001ba40a098e43c7b127`.
- Aligned bounds before game-axis conversion: X -0.950605..0.949649 m, Y -2.030205..2.167214 m, Z ~0..1.120221 m.

OVRCABH4 conversion and independent second pass:
- 66,391 triangles
- 55,533 vertices
- 44 groups
- 12 materials
- 3 source images
- 234 glass triangles
- 4,153,332 bytes
- Output SHA256: `a4608bd0d9c8a4743cddd17a0306276fb10aa24628c5817ce0e2bced67058dd1`
- Converter audit: READY_PRIVATE_CONVERSION
- Independent OVC4 parser/hash/geometry validation: PASS
- Runtime/Quest3 test: NOT YET RUN
- Native dashboard binding: none; use the existing independent live dashboard overlay path.

Default gate:
- Existing 328 GTS slot donor remains Ferrari 308/QV at 139,216 triangles.
- The new exact 328 GTS candidate is substantially lower-detail, so it is **optional exact private only**, not a silent replacement.

## Ferrari 575 Superamerica — new NFS Shift source inspected, rejected as default

Newly acquired source:
- Ferrari 575M Superamerica, NFS Shift-origin model converted to NFS Carbon.
- Archive SHA256: `dd365ca30770cc07fbf4663054743a5be37fcb57edd2902c8b9cda03a7e7d49a`.

Important parser correction:
- A generic NFS parser initially misread Carbon 144-byte mesh entries and over-counted faces. That result was discarded.
- Carbon-specific mesh entry parsing reports 48,919 LOD-A triangles when mutually exclusive roof T0/T1/T2 A-state meshes are all summed; an actual selected roof state is lower.
- The source contains a detailed interior object, but it is still not an upgrade over the existing exact Assetto Garage Superamerica OVC4 (51,444 triangles), and is far below the current 575M donor (200,071 triangles).
- 12 DXT1/DXT5 textures were recovered from the nfsu360 wrapper/JDLZ layout, confirming the archive is not texture-empty.
- Result: **do not replace either the current donor or the existing exact optional Superamerica OVC4**.

## Ferrari F430 Spider — TDU/GTR2 source inspected, rejected as replacement

Newly acquired source:
- Ferrari F430 Spider GTR2 addon by scca1981, stated as converted from Test Drive Unlimited.
- Archive SHA256: `bb09e1c8d8935b2bd2634052074cedb486d3c82f0b4c2c296815389af18b9f33`.
- Separate chassis, cockpit, wheel and texture containers were extracted.
- All 29 GMT meshes imported with the official Blender GTR2 GMT Importer v0.8.4 without importer failure.
- Imported scene is about 65.6k triangles before removing showroom/default helper geometry.
- It is below the already retained exact F430 Spider private OVC4 (77,979 triangles) and far below the Scuderia Spider 16M donor (565,172 triangles).
- Source page restriction/credits do not provide a safe redistribution grant; keep inspection private.
- Result: **no replacement**.

## Current-source sweep

- A large Assetto Corsa F430 2004 2-in-1 mirror was found, but the listing points back to an original Patreon source and the mirror does not establish cross-game conversion/redistribution permission. It was not used.
- The 2026 GTA V Enhanced F430 Spider source remains excluded because the author explicitly prohibits conversion to other games.
- The current Superamerica listing resolves to the same Assetto Garage source already converted on 2026-11-18; no higher-detail exact replacement was verified.
- For 328 GTS, paid high-detail sources remain available, but no newly verified free exact full-cockpit source exceeded the donor quality gate.

## SSOT status after this pass

- Exact external private candidates available: 14/16 if counting optional exact sources, because 328 GTS now has a verified exact private OVC4 candidate in addition to the prior 13.
- **Default high-quality exact package remains 13/16.** 328 GTS, 575 Superamerica and F430 Spider stay on the higher-detail donors by default until an exact model passes the no-quality-regression gate.
- 575 Superamerica and F430 Spider already have exact optional OVC4 candidates; this pass does not score their re-verification again.
- No Quest 3 runtime success is claimed for the new 328 exact candidate.
