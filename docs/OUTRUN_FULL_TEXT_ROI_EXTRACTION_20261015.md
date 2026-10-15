# OutRun 2006 — Full-source text ROI batch extraction, 2026-10-15

**Task ID:** OUTRUN-FULL-TEXT-ROI-EXTRACTION-20261015-1739  
**Scope:** Korean localization only; do not touch VR/FFB/DX11/DXVK.  
**Source of truth:** `korean-localization-recovery-20260928`.  
**Status:** Source-wide **ROI PROPOSAL EXTRACTION COMPLETE**, **NOT semantic phrase extraction QA**, **NOT ImageGen approved**.

## Executed and audited

- N100 input inventory: `/home/chatgpt-runner2/work/image-src/text_roi_batches/full_source_inventory.json`, **108** registered full atlas texture variants with **746** translated phrases registered across **86** mapped variants.
- **85** sources traversed and processed; **22** no-localization/no-bound-phrase variants deliberately skipped, **1** source (`Q046_AA04D779_BASE_READABLE_FLIPY.png`) **HOLD_FULL_SOURCE_MISSING**.
- **1,540** extracted proposed ROIs. Every ROI has *two actual files*: `english_roi.png` and `imagegen_input_REVIEW.png`, for **3,080 PNG files** totaling **402,114,704 bytes**. Each ROI includes SHA-pinned `manifest.json` with native source xyxy, upscale, potential translation options, DDS path/provenance and `RUNTIME_VALIDATION=UNTESTED`.
- Independent pass over all 1,540 ROI pairs found **0** PNG mode/dimension/SHA mismatches. Checks establish file integrity **only**, not semantic source matching, safety, correct text content or crop quality.
- **327** candidates touch ROI alpha boundaries and must be revised or HOLD; no partial glyphs may be sent to ImageGen. Source/original comparison is incomplete for **1,538** candidate ROIs derived from SHA-verified *previous full atlas reassembly* (not old individual tile inputs). **2** use pinned full-HD direct images from GitHub manual pack, but remain proposals. No candidate in this bulk job was auto-approved for ImageGen.
- Connected-alpha segmentation does not distinguish letters from adjacent cars, logos or background art. Q043 and Q044 annotated previews show mixed/merged regions: they are **NOT** one-phrase model inputs without human mapping and explicit masks/PSD.
- Additional manual phrase crop reference: 15 Q043/Q044 regions under `/home/chatgpt-runner2/work/c_salvage_text_roi/manual_phrase_20261015/`, of which 12 touch alpha edge and all retain SOURCE/DDS QA HOLD. Never auto-promote.
- Previously approved *separate* Q104 full-HD source ROI `OutRun Mode`→`아웃런 모드` remains in `work/image-src/text_roi_batches/production_manifest.json`; this job never consumed or rewrote its queue, send receipt, Library proof, or A/B data.

## Output and reproduction

- N100 output: `/home/chatgpt-runner2/work/c_salvage_text_roi/full_bulk_20261015/`:
  - `sources/<source basename>/<number>/english_roi.png`
  - `sources/<source basename>/<number>/imagegen_input_REVIEW.png`
  - `sources/<source basename>/<number>/manifest.json`
  - `sources/<source basename>/review.jpg` (one full-atlas visual index for each processed source)
  - `summary.json`, `bulk_audit.json`
- GitHub scripts: `tools/localization/full_text_roi_bulk.py`, `tools/localization/audit_full_text_roi_bulk.py`. Script expects the manifest and canonical/full reconstructed source files to be present on N100. Do not run the script while the same output path exists without first using a new isolated output name.
- GitHub evidence: `localization/graphics/role_C_salvage/20261015-bulk-roi/ROI_EXTRACTION_INDEX.json` and `ROI_AUDIT.json` (read-only audit mirror; **PNG binaries remain on N100**).

## Mandatory next step before A/B dispatch

Obtain full canonical HD PNG or decoded/verified native DDS for the remaining variants (reassembly alone is not DDS equivalence). For every visible translation phrase:
(1) individually identify exact lettering + outline + shadow bbox and correct Korean string,
(2) ensure no edge clip, car/icon/background contamination, or adjacent text,
(3) if alpha merged into sprite art, use pinned Photoshop text layers or a separately reviewed mask,
(4) issue one isolated transparent or reference ROI per phrase, with SHA and original position,
(5) authorize explicit additions to the **new** ROI production manifest/queue only after QA.
The **1540 unreviewed proposals must not enter automatic A/B batches** and must not be interpreted as 1540 complete translated phrases.

No ImageGen, C1/C3 independent QA, final native-format DDS or in-game validation was performed in this job. `RUNTIME_VALIDATION=UNTESTED`.
