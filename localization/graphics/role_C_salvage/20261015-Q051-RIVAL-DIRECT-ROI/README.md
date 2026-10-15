# Q051 Rival — direct canonical source ROI (C / TEST_ONLY)

- Task: `C-ROI-Q051-RIVAL-20261015-2303`; 2026-10-15 KST.
- English `Rival`; official Korean `라이벌`. This folder holds **one complete English text phrase**, not Korean generated content.
- Exact source: GitHub asset branch `korean-localization-recovery-20260928`, `localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds`, SHA256 `5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67`, PC 4096x2048 RGBA HD DDS.
- Complete readable source PNG `q051_FF2462BB_FLIPY_CHECK_ORIENTATION.png`, SHA256 `2da1b6f01219356ddc6ea925bd8fcd4afd37d9040eb48081a40861cc649da6f0`; identical to the direct pinned GitHub DDS after FLIP-Y: **0 different pixels / 8,388,608**.
- Native ROI xyxy `[2325,520,2478,608]` (153x88); alpha-backed entire glyph+outline+shadow, at least 2 transparent pixels on each side; no other text. Pixel-exact native crop SHA in roi_manifest.json.
- 4x upscale to 612x352 RGBA with aspect ratio kept; see imagegen_input_upscaled.png and its SHA256 in roi_manifest.json.
- Exported through pinned `tools/localization/text_roi_source_pack.py` schema `outrun-hd-text-roi-v1`; SOURCE_ROI_QA_TEST_ONLY.json provides source/pixel QA.
- Output is an **isolated ImageGen input candidate only**. ChatGPT image generation, DDS compose, CLEAN, independent C1/C3, real-game validation: NOT_RUN; `RUNTIME_VALIDATION=UNTESTED`.
- Any future generated Hangul should be restored with **aspect ratio preserved** into measured UI cell/UV safe bounds; width difference alone is not rejection. No automatic guessing of masks or CLEAN, no A/B queue/state modification, and no redeployment here.
