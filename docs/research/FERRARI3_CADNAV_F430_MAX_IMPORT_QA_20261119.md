# Ferrari 3 remaining exact models — follow-up source test (2026-11-19 KST)

## Scope and baseline
This is **new source acquisition, actual MAX-to-Blender-to-GLB import, and rejection QA**, NOT a new default vehicle or Quest 3 gameplay validation. Preserve the user's working high-detail donor models. Baseline as independently documented in the earlier `FERRARI3_REMAINING_EXACT_SWEEP_20261119.md`: private exact-source candidates **16/16 counting optional**, default high-quality exact **13/16**.

## New Ferrari F430 F1 Spider source actually acquired

- Source page: https://www.cadnav.com/3d-models/model-52211.html (CadNav model #52211, labelled Ferrari F430 F1 Spider).
- Site description claims **527,622 polygons** and a 9.02 MB Autodesk 3ds Max `.max` file. Crucial site metadata also says **Textures: No / Materials: No**, license **Non-commercial**.
- The archive's readme permits modifying the model within a project with attribution, but prohibits separate redistribution; because the source page is stricter, treat this as **private/non-commercial only, no model redistribution**. The archive does not establish that original underlying rights transfer.
- Source ZIP was downloaded directly via the site download link and statically inspected, without executing its contents:
  - ZIP size **2,448,127 bytes**, SHA256 `c92a8ae7febc1bfdabc28acbaed77eb37fd9f35728604cb4d1be7dbf15a89cca`
  - One main `cadnav.com_model/Models_H1204A072/ferrari F430.max` at **9,461,760 bytes**, SHA256 `a142941d8c0817483259b1dbe6ea761ea9f8ee4b8e084c6a457877ae8844b17d`.
- Converter: [NRGSille `io_scene_max` 1.9.2](https://github.com/nrgsille76/io_scene_max), loaded by **Blender 5.2.4 LTS** with CPU threads limited to two. Both matrix options finished; no 3ds Max license or executable was required.
- First import (`use_apply_matrix=True`) actually produced **127 mesh objects, 145 total objects, 115,091 mesh polygons, 94,713 vertices, 76 UV layers, 1 material, 0 images**.
- GLB export completed. Private unaligned/untextured GLB **4,295,776 bytes**, SHA256 `15d90b23a94a80122fa72683ab48753d01cdc559874376b6c63513a132f028f4`. The GLB was independently reopened by Blender and a **640×400 grayscale QA render** was generated.
- The render shows **stray elongated mesh strips and visibly misplaced wheel/body components**. Object names include `MLancer_Wheel*` and generic imported primitive names. Source car identity, all wheel fit, cockpit quality and correct transforms are **NOT verified**.
- Alternate import (`use_apply_matrix=False`) also completed but had grossly expanded bounds (approx X -2164..757, Y -3001..20499, Z -1597..1597) versus the first already misaligned scene (approx X -46..101, Y -71..181, Z 0..42), so it **did not fix the geometry fit**.
- Advertised polygon count **527,622** is **not** the actual geometry recovered by this open-source importer (**115,091 mesh polygons**). It could be an application subdivision/modifier discrepancy, incomplete importer recovery, or source-listing mismatch; **do not equate the two**.

**Decision: `CONVERSION_TECHNICALLY_PASS__QUALITY_GATE_FAIL__NOT_PROMOTED`.** Do not generate an OVC4 default replacement from this untextured, visually misassembled candidate. Existing exact optional 77,979-triangle F430 Spider and 565,172-triangle 16M donor remain unchanged; no Quest 3 runtime claim.

### Private on-host evidence — not for redistribution
All files in N100 home-authorized directory:
`ferrari_resume_20261119/cadnav_f430_f1_spider/`
- `f430_cadnav_52211_untrusted.bin` (ZIP download, do not execute)
- `extracted/cadnav.com_model/Models_H1204A072/ferrari F430.max`
- `blender_import_report.json` and `blender_import_no_matrix_report.json`
- `f430_cadnav_import_unaligned_UNTEXTURED_PRIVATE.glb`
- `f430_cadnav_IMPORT_NO_MATRIX_PRIVATE.glb`
- `f430_cadnav_untextured_qa_preview.png`
- `blender_render_report.json`, consoles and disposable import driver scripts.
Third-party model binary and derivative are intentionally **not committed to GitHub**.

## Additional search false-positive elimination

1. [Ferrari 575 Maranello F1 Shift 1.16](https://www.modland.net/assetto-corsa-mods/cars/ferrari-575-maranello-f1-shift.html): the description's mention of *a Superamerica version* is in generic 575M vehicle history; the v1.16 changelog lists tire settings and LOD fixes. No explicit evidence that the **Superamerica body/roof variant** is provided; do not infer a new exact model from that listing.
2. [Ferrari F430 PGR4 Update](https://www.gtplanet.net/forum/downloads/ferrari-f430-pgr4-update.7599/): the resource is described as physics/sound adjustments rather than a newly verified F430 **Spider** body asset, so do not count or convert as a new exact source.
3. [Ferrari F430 Spider, Behr Bros / 3DExport](https://3dexport.com/3d-model-ferrari-f430-spider-3607): a plausible **paid** high-resolution exact Spider with detailed interior, separate roof/interior/exterior and claimed OBJ resolutions 181k–888k polygons. **Not purchased or imported**. Distribution/license checks and actual meshes required if explicitly acquired.
4. For 328 GTS, the prior exact 66,391-triangle OVC4 remains optional; new free high-quality full-cockpit evidence was not established in this pass.
5. For 575 Superamerica, the prior exact 51,444-triangle OVC4 remains optional; no newly verified higher-quality roof/cockpit source was found.

## Invariants
- Exact model candidate inventory: **16/16 optional-inclusive**.
- Default high-quality exact model inventory: **13/16**, no changes.
- No change to `ExternalCars` installed defaults, source branch runtime binary, OutRun game scripts or other mod repositories.
- Actual Quest 3 runtime acceptance **not performed**.
- This is an acquisition/diagnostic follow-up **without a new approved model or OVC4 promotion**. AI2 score change **+0**; no duplicate points for the earlier 328 model or source-only research.
