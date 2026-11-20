# Ferrari 3 remaining exact HQ models — source recheck (2026-11-20 KST)

## Scope / source of truth
Research follow-up to [Ferrari16 exact-variant audit](FERRARI16_EXACT_VARIANT_AUDIT_20261118.md) at branch `vr-ferrari16-v4-integrated-20261118`. Scope is exact high-quality 328 GTS, 575 Superamerica, and *standard* F430 Spider, without changing or silently downgrading the working/default game package.

**This pass is public-source research only**: no downloaded third-party car binaries, new Blender/OVC4 conversions, runtime launch, Quest 3 visual validation, or default asset promotions are claimed. Current accepted accounting is **13/16 high-quality exact default**, **16/16 exact-source candidates when lower-detail optional private candidates are counted**.

## New independently verified quality blockers and source context

### Ferrari 328 GTS
- [3D CAD Browser: Ferrari 328 GTS (1985)](https://www.3dcadbrowser.com/3d-model/ferrari-328-gts-1985) exposes **66,381 *polygons***, **39,065 vertices**, 44 objects, 17 materials, **0 textures** and **no UV mapping** on the live product page (reviewed 2026-11-20). It needs an account with uploads or a paid account for the download. Geometry polygons are not directly comparable with OVC4 triangles; independently of that caveat, zero textures/no UV makes it **UNSUITABLE for unmodified HQ dashboard/normal-map replacement**. Do not mistake the site's general "game-ready" description for a verified textured cockpit.
- [88Cars3D 328 GTS](https://88cars3d.com/product/ferrari-328-gts-3d-model/) live product view shows **EUR 29**, and claims BLEND/FBX/OBJ/GLB, seats, dashboard, gauges, textured materials; however, original download, mesh density, texture dimensions and actual interior snapshots have not been inspected; **PAID / UNVERIFIED**. Search engine snippets also surfaced a contradictory EUR 199 number: privilege the opened product-page price as observed at check time, and recheck before any purchase. No payment authorized.
- [3DExport / SQUIR 328 GTB GTS](https://3dexport.com/kr/3d-model-ferrari-328-gtb-gts-1985-1989-76188) lists 500,000 polygons, textures, UVW mapped and FBX/OBJ/C4D/MAX; not PBR, paid, mesh/true GTS/open roof and cockpit details unverified. License disallows standalone redistribution; not acquired.
- Prior verified exact GTA SA-derived 328 optional OVC4 is **66,391 triangles / 12 materials / 3 images**. Existing default 308/QV donor is **139,216 triangles**. No new authorized free exact HQ source beats quality gate. **DEFAULT UNCHANGED**.

### Ferrari 575 Superamerica
- [Assettoland Ferrari catalog](https://assettoland10.wixsite.com/assettoland/ferrari) includes **Ferrari Superamerica by Assettogarage**; it is the already researched source family rather than an independently confirmed high-detail upgrade. Prior exact Assetto Garage optional is **51,444 triangles**, with a separately verified 2-needle native-dashboard optional package; game dial direction and Quest3 visual gate remain untested.
- [2026-11-04 CGTrader Ferrari 575](https://www.cgtrader.com/3d-models/car/sport-car/ferrari-575-2002-supercar-3d-model) has 191,286 triangles and base/normal map claims, but the source is a **575M coupe** (2002), not a rotating-roof Superamerica. **REJECT AS EXACT** irrespective of its high geometry count.
- [FlatPyramid Ferrari Superamerica](https://www.flatpyramid.com/3d-models/vehicles-3d-models/brands/ferrari/ferrari-superamerica/) lists 46,670 polygons, 43,649 vertices, textures and a $55 paid source; no evidence it beats the retained optional exact source or contains a detailed dash.
- Actual 575 Superamerica [driver-eye interior/roof photo reference](https://www.dkeng.co.uk/Vehicle_Archive/825/ferrari_575_superamerica.html) can be used for open-cockpit and tri-vent dashboard visual comparison only. Do not distribute copyrighted reference photos as assets.
- Current donor default 575M has **200,071 triangles**. No exact HQ upgrade validated. **DEFAULT UNCHANGED**.

### Ferrari F430 Spider
- [BeamNG F430 Spider v1.1 ModLand](https://www.modland.net/beamng.drive-mods/cars/f430-spider.html) displays a **445.1 MB** ZIP, uploader "Fairy Evolution", PBR, detailed engine/cockpit, animated dashboard, shifter and handbrake, four configurations; a separate [VGTimes mirror](https://vgtimes.com/games/beamng.drive/files/92027-ferrari-f430-spider-v1-1-0-38-x.html) credits **PrivateMods as author** and **STR1KE as uploader** (2026-02-15). Author/original distribution page and permission for cross-game asset conversion **NOT VERIFIED**. Archive size does not prove polygon count. High-priority quality candidate for owner-authorized *private* file inspection only, not automatic import. Live ModLand download endpoint returned a **403** to the available browsing interface.
- [BeamNG published modding guidelines](https://www.beamng.com/game/support/policies/modding-guidelines/) require original authorship or permissions for use of another user's content; third-party mirrors are not a clear redistribution grant.
- [Opperslang & GADU Boyz F430 Assetto Corsa source listing](https://arcmitecollective.com/mods/opperslang-gadu-boyz-ferrari-f430-826de4d3) describes a free regular **F430** using GT6/GT7/FM7 assets, but does **not establish a stock F430 Spider open-top variant**; classify `EXACT_BODY_UNVERIFIED` and do not claim gain over existing model.
- [GTPlanet Ferrari F430 PGR4 Update](https://www.gtplanet.net/forum/downloads/ferrari-f430-pgr4-update.7599/) is a **sound/physics update requiring a separate vehicle source**, not a new standalone high-detail Spider mesh. Reject as an alternate geometry source.
- Previous exact standard F430 Spider optional is **77,979 triangles**; 565,172-triangle Scuderia Spider 16M remains higher-detail but wrong trim donor. New 2026 Enhanced GTA V exact Spider upload retains an explicit **no cross-game conversion** restriction (see baseline audit); continue excluding. **DEFAULT UNCHANGED**.

## Next actual work, gated
1. F430 Spider: contact/find the original PrivateMods author distribution and consent; if legitimately available inspect original ZIP *without running code*, parse DAE mesh groups + DDS/PNG texture inventory + dashboard hierarchy and verify **actual stock open-top** configuration, then decide if a separate optional OVC4 test is justified.
2. 328 GTS: search creator-owned free permitted 328 GTS Blender/FBX with usable UV and real textured dashboard. No speculative model purchase and no promotion of untextured CAD source.
3. 575 Superamerica: seek explicit rotating glass roof geometry and genuine cockpit with image/mesh quality superior to 51k-triangle optional; avoid 575M Maranello false positives. Use the DK Engineering interior reference to align 575 analog gauges/tri-vents when allowed.
4. For all three: exact body + provenance -> source SHA -> triangles/UV/PBR/normal/materials -> bounds and wheel clearance -> native speed/RPM pivot or overlay -> isolated OVC4 static PASS -> **actual Quest3 driver-eye/VR gameplay** before default/finished status.
5. Do not change the currently normal-running non-modeling VR branch as part of model-source research.

## AI2 scoring
Research-only follow-up and unverified source listings are **+0**, no duplicate completed car, conversion or Quest3 result. Latest independently confirmed GitHub `ai-dev-lab@main/AI_SCOREBOARD.md` at 2026-11-20 09:31 KST is **2875** (commit `1ef13045f151c8dd02672f84b5350653d051afe8`): **2875 + 0 = 2875 AI2 cumulative points**. AI1 not involved.
