# Google Drive ImageGen PNG → original-size atlas / glyph layer / DDS smoke test (2026-10-14)

- RUN_KEY: `OUTRUN-DRIVE-PNG-TO-DDS-SMOKE-20261014`
- Status: **TEST_ONLY / NOT DEPLOYABLE**
- Generated input: Google Drive `OutRun_Korean_PNG_20261014` (ImageGen PNGs originally copied from ChatGPT Library), https://drive.google.com/drive/folders/1G_rJIDoiYbkSg9rfT2oLETNFW6ZVYh17
- English source: `OutRun_HD_EN_TILES_01_of_10.zip` in Google Drive `OutRun_N100_TRANSFER_20261014`. HD-source tiles are reused, not a generated image as plate.

## Executed tests

| Asset | Source and reconstruction | Extraction | DDS generation | Mechanical QA | Gate |
|---|---|---|---|---|---|
| Q012 / D6DC1380 | 256×64 original PNG, `READABLE_NORMAL`; Korean `계속?` from generated RGBA `image-gen-1(3).png` | Exact generated alpha-text bbox (608,249)-(1620,546), alpha overlay confined to English glyph bbox (8,10)-(248,44) | legacy BGRA32, 1 mip, 256×64; SHA256 `6cb058cb1f2a113cf405cca09f5417b323318339a87ead1c4405c35d9d954a2a` | 0 changed pixels outside intended bbox, 65664 bytes, exact RGBA↔DDS roundtrip | HOLD original DDS header not byte-compared; glyph visual QA/game UNTESTED |
| Q032 / DCC7B488 | Three original tiles 683+682+683 assembled to exact 2048×1024; every reconstructed tile byte-exact at pixel level | Extract text `종합 랭킹` from generated RGB `image-gen-3.png`; keep source speech balloon/icon, inpaint only English lettering | flip-Y test view converted to legacy BGRA32 DDS, 1 mip, 2048×1024; source raw-sprite orientation NOT confirmed | 0 changed pixels outside English text bbox, 8388736 bytes, exact RGBA↔DDS roundtrip | HOLD: source text touches left crop boundary (clipping risk); inpaint/background ghosting; orientation/header not verified; game UNTESTED |
| Q034 icon fragment | 819×681 source tile with red `A` plus adjacent heart artwork | Alpha extracted from generated RGB `image-gen-5.png` via dark matte. Source image cuts icon at output bottom edge. | Not composited into DDS: protected original icon left untouched | Mask extraction mechanically possible | HOLD: icon incomplete and unauthorized style change |

### What this demonstrates

1. The previously blocked Library raw-byte access can be bypassed **with authorized Google Drive exports** of the copied generated PNGs; they can be read and processed locally.
2. Original multi-tile atlas geometry can be reconstructed exactly from HD tiles.
3. Transparent text/icon layers can be isolated, scaled to original label ROI, and encoded to mechanically valid BGRA32 test DDS, preserving pixels outside edit areas.
4. A direct image-to-DDS conversion is **not** suitable: generated dimensions/alpha/background often differ, and some outputs crop letters/icons.
5. This test **does not** validate original DDS source header/mip/format or per-sprite mixed transform, nor native/75%/50% glyph legibility, C QA, or game runtime. No production queue status is promoted.

### Artifacts

An independent local ZIP `OUTRUN_DRIVE_IMAGEGEN_TO_DDS_SMOKE_20261014.zip` contains the exact original and candidate PNGs, title-cleaning preview, alpha-only layers, both test DDS files, generated icon test, JPEG original/Korean comparisons, QA_RESULTS.json and the proof-of-concept script. The ZIP is **not** in this GitHub branch (binary game artwork remains off repo).

Review required: verify actual HD DDS raw bytes (header, FourCC/mips/orientation), correct clipped/ghost text areas and proper icon extraction before any deployment. `RUNTIME_VALIDATION=UNTESTED`.
