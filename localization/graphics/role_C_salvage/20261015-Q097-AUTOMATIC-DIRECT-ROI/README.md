# Q097 Automatic: direct-HD source text ROI (TEST_ONLY)

New, independent **one-phrase** source candidate for A/B ImageGen staging. No ImageGen call, no Korean output, no DDS composition, no C1/C3 or game approval.

- Original GitHub thp32tt/OutRun2006Tweaks, asset branch `korean-localization-recovery-20260928`, actual HD DDS `localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_selector_cvt_Exst/411827E_512x512.dds`.
- Original DDS SHA256 `bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364`, Git blob `d488d1a0ccd71b0f38410ece0b90e530e2c8ff71`. The DDS basename is a legacy 512×512 label; **actual decoded source is 2048×2048**.
- Direct DDS decoded to RGBA and flipped vertically into the readable full-original PNG. Verified pixel-for-pixel equal to the independently pinned full-original PNG; **not** reconstructed from any of the old 986 tiles.
- Reviewed Q097 mapping: `Automatic` → `자동`. Other source labels, vehicle names, brands, music and artwork are outside this single ROI.
- Full original PNG: `Q097_full_original_readable.png` SHA256 `2ecc253ac9db49a9c1189f1f814d562a45462b660af94877ce1f66737cfe58af`.
- Crop from full original `[0,170,552,296]` (xyxy), native `552×126`; complete lettering including outline/shadow alpha bbox `[6,178,543,288]` with 6/9/8/8 px transparent margins (left/right/top/bottom).
- `english_text_roi_native.png` SHA256 `0cb0cdd7150d9caaaed9a273afdb609d910b00e9ad144aeb87efcac79b4d0454`; 4× `imagegen_input_upscaled.png` 2208×504 SHA256 `8a2c9028672c1497fe2d71af3ccbc5039f2050e777586424ce27734678c95263`.
- Extracted with pinned `tools/localization/text_roi_source_pack.py` using `outrun-hd-text-roi-v1`; 2px alpha-edge guard passed on all four sides, no phrase clipping.
- New ROI is a **TEST_ONLY input candidate**. ImageGen conversion, exact UI-cell/UV fit, correct aspect-preserving re-scaling, clean plate and DDS remain to be reviewed.
- A/B production requires a distinct verified ROI-index + separate state/queue and user-controlled Portainer deployment. **Do not restore old `ab_batch_queue.py` 986-tile dispatch.**
- Old A/B queue/state, generated image history, prior artifacts and SHA are unchanged. `RUNTIME_VALIDATION=UNTESTED`.

No production pass or user playtest is implied by this evidence commit.
