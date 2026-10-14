# OutRun 2006 HD GUI — C 복구·중간본 합성 슬롯 (2026-10-15)

Status: **APPROVED DESIGN / NOT DEPLOYED / NO CLAIM OF FINAL DDS**
Source of truth: `thp32tt/OutRun2006Tweaks` branch `korean-localization-recovery-20260928`.
Scope: HD GUI / localization only; excludes VR, FFB, DX11, DXVK.
Trigger: User reports that ChatGPT image generation is rate-limited from approximately 01:00 KST for 16 hours. **Do not infer the exact reset instant or attempt to evade that cap.**

## Objective and separate ownership

Add **logical worker C / C-SALVAGE** that reuses **existing** A/B English originals, generated Korean PNG candidates and verified upstream PSD layers to create reproducible **text-only assets, clean plates, composites, and native-format DDS test candidates**. **C performs no native ChatGPT image generation** and needs no additional ChatGPT account/tab or paid API. It may be run manually using local Python/GitHub Actions, independently of the live Portainer browser controller.

Existing C1 remains the independent reviewer, not a production actor for its own approved outputs. Existing A/B roles, active A/B/C1 tabs, schedules, source queue and in-flight batches stay unchanged. C outputs must not be marked C1_PASS by C itself. Portainer deployment/restart, automatic sending, game publishing and runtime approval stay **user-manual**; GitHub policy alone does not deploy a C container/tab.

## Measured inventory (2026-10-15; not a QA pass)

N100 file evidence:
- `work/image-src/ab_batches/candidate_outputs/A`: **110** candidate PNGs, generated from 22 completed five-image batches; A batch 23 is SUBMITTING.
- `work/image-src/ab_batches/candidate_outputs/B`: **180** candidate PNGs, generated from 36 completed five-image batches; B batch 37 is SUBMITTING.
- **290** locally exported, **UNAPPROVED** candidates span **27 unique HD texture queue IDs** (A six, B twenty-one).
- Per-batch `library_evidence` for 22 A + 36 B recorded five exact generated-vs-library SHA matches per completed batch; this establishes image preservation, **not** correct translation, dimension, background, DDS or game readiness.
- Manifest has **986** planned tile inputs, **985** PNG integrity-valid and **1** corrupt. Generation count / input count is not a finished-localization rate.
- In sampled batch A-0001/A-0022/B-0036, output dimensions differ from source. Existing generated PNGs must **not** replace full source atlas or be scaled indiscriminately.

GitHub `localization/graphics/plate_library/PSD_UPSTREAM_FULL_INDEX.json` at upstream `Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`:
- Of 27 candidate texture IDs, **22** have ≥1 indexed corresponding PSD, **10** have a copy marked `copied_into_branch=true`, **12** have a PSD indexed externally but not marked copied; **5** have no catalog match (**q012, q036, q102, q128, q130**).
- SHA/name match is **not** proof that text is isolated, that PSD RGB/alpha match the canonical HD DDS, or that derived CLEAN is acceptable.
- Existing `tools/localization/psd_layer_workbase.py`, `tools/localization/plate_library.py`, and `tools/localization/production_pixel_guard.py` should be reused, not replaced by an untested new encoder.

## Required C stages (one native asset/ROI at a time)

1. **INDEX / LOCK INPUTS**: per texture ID list all A/B candidate tiles, source HD DDS path/SHA/actual width, height, DDS FOURCC/bit masks/mips; original-readable crop/SHA, source transform, UI cell/UV-safe bounds and queue translation. Pin generated PNG bytes/SHA, link to source tile and record image-generation status and library matching evidence. Prefer unique 27 texture families over 290 independent DDS outputs. If mapping ambiguous, `HOLD_MAPPING`.
2. **PSD-FIRST**: lookup a locally copied SHA-verified PSD from `PSD_UPSTREAM_FULL_INDEX.json`, inspect with `psd_layer_workbase.py inventory/separate/export`. Isolate English face, outline and shadow into separate RGBA layers and render a text-free native-size PSD CLEAN. Verify it against actual canonical HD DDS at RAW/readable orientation. If only external PSD is catalogued, copy from the pinned upstream commit/blob SHA, never latest HEAD; log source, authorship and reuse rights. If no PSD or non-equivalent PSD, fall back to SOURCE DDS.
3. **TEXT-ONLY SALVAGE**: for each *existing* Korean generated candidate, manually identify the actual Korean phrase and its effects (not cars/background/icons). Produce a dedicated transparent text/effects RGBA layer and a separately verified alpha mask. Generated image and source resolutions differ, so **never resize the whole scene**: crop one phrase, then scale that phrase with aspect ratio preserved to fit a measured safe UI cell. Retain effect/face layers and literal translation proof. Reject mixed labels, fake Hangul, clipped strokes and adjacent art. Save `korean_letter_only.png`, `korean_mask.png`, source/output SHAs, crop bbox and mapping. Even if CLEAN is unavailable, **store the isolated lettering for future reuse**; mark `LAYER_ONLY_READY`, not a final candidate.
4. **SOURCE CLEAN fallback**: if PSD CLEAN is absent or fails byte-level comparison, derive a mask for all original English glyphs/effects from the exact canonical HD DDS, respecting alpha and text bounds. When original glyphs sit on genuinely transparent pixels, clear only the checked removal mask. For opaque/complex underlying artwork, use patch reconstruction or explicitly reviewed inpainting constrained to the text ROI, labelled `CLEAN_REVIEW_REQUIRED`. **Inpainting is never presumed pixel-exact, and the original background is never fabricated and auto-approved**. Save `english_original.png`, `source_mask.png`, `clean_candidate.png`, `plate_review.png`; protect non-text RGB/alpha exactly. Existing approved plate-library object is preferred and immutable.
5. **NATIVE COMPOSE / INTERMEDIATE**: place approved isolated Korean text/effects on verified CLEAN in native readable coordinates, then apply the exact per-sprite inverse RAW transform. Keep each UI cell's x/y/width/height pinned and preserve the untouched canonical atlas pixels. Native RGBA source-vs-final must show zero changed pixels outside edited regions and zero protected-pixel changes, zero overlap/clipping, no remaining visible English, coherent alpha. Produce `intermediate_readable.png`, `intermediate_native_raw.png`, side-by-side original/clean/final review JPG and JSON manifest with `TEST_ONLY` or `HOLD` **but not a claimed C1 or game PASS**. Partial composite may leave untranslated regions explicitly recorded; do not mark entire atlas complete.
6. **DDS TEST + QA + FINAL GATE**: reuse actual source DDS encoder preserving dimensions, FOURCC/bit masks/mip count, color space and orientation, and decode the persisted DDS. Compare saved bytes/header + decoded RGB/alpha, compressed blocks touching protected pixels and 100/75/50 readable previews. Unsupported encoder/complex mip chain => `ENCODER_UNSUPPORTED` / HOLD, not a converted file. Mark `C_DDS_TEST_ONLY`, send to **independent C1** review (4–8 different candidates), then C3 for high-risk P0/P1/shared-HUD, finally user in-game visual review. `FINAL_APPROVED` and patch promotion only after all required gates; until game executed `RUNTIME_VALIDATION=UNTESTED`.

## Priority and throughput

1. **LAYER_ONLY** can proceed on existing A/B candidates immediately, without new image generation and without a matching PSD, after manual text segmentation.
2. **CLEAN+COMPOSITE** first for PSD locally copied and actually layer-separable/native-aligned: **q032, q092, q098, q099, q104, q107, q112, q116, q119, q121**. Prioritization indicates PSD presence only, not an approved CLEAN.
3. **PSD FETCH + INSPECT** for **q034, q035, q043, q094, q095, q097, q100, q101, q103, q106, q111, q132**. Source files are often large; perform reads/extraction via GitHub Actions/self local workspace instead of loading the N100 with bulk processing.
4. **DDS-FIRST CLEAN** for PSD-unmatched **q012, q036, q102, q128, q130**, with editable mask and independent plate check.
5. Rework/generated artifacts remain reproducible and content-addressed. One asset's failure never blocks extraction of another. Do not retry native ImageGen during the reported cooldown.

## Isolation, outputs, acceptance

Suggested non-live workspace: `localization/graphics/role_C_salvage/<YYYYMMDD>/<queue_id>/<source_sha_prefix>/` and a one-row-per-text-region manifest. Never replace `hd_candidates`, `approved_dds`, A/B outputs or `asset_queue.csv` status with an unreviewed C file. Do not treat a sampled missing status as all 290 failing the same way.

For every job:
`source_dds_sha256, source_png_sha256, imagegen_output_sha256, psd_upstream_commit/blob_sha/psd_sha256 (or none), chosen_psd_layers, original_text, approved_Korean_text, source_roi, generated_text_roi, generated_mask_sha256, clean_sha256, korean_layer_sha256, composite_sha256, DDS_header_and_mip_probe, preserved_pixel_diff_count, crop/overlap_qa, independent_reviewer, QA_status, RUNTIME_VALIDATION`.

State progression:
`DISCOVERED → SOURCE_VERIFIED → [PSD_LAYER_SEPARATED | DDS_CLEAN_REQUIRED] → LAYER_ONLY_READY → CLEAN_REVIEW_REQUIRED → CLEAN_INDEPENDENT_PASS → C_COMPOSITE_TEST_ONLY → C_DDS_TEST_ONLY → C1_REVIEW → C3_IF_REQUIRED → USER_GAME_REVIEW → FINAL_APPROVED`.
Allow `HOLD_MAPPING/PSD_MISMATCH/NO_KOREAN_TEXT/CLEAN_FAIL/ENCODER_UNSUPPORTED/REWORK` at any stage. No invented PASS.

## Non-goals and deployment

C is a **fourth logical recovery role**, **not** the existing Docker slot labelled `C` (currently occupied by C1 reviewer), and **not** an extra ImageGen browser/tab. `controller_roles.json` may declare it as `manual_offline_no_imagegen` without editing `controller_tab_order` or `schedule_dispatch`. A real fourth Portainer slot, if later required, needs runtime controller and Compose capability review, isolated volumes, independent data labels and user's manual Pull/redeploy. In particular never silently replace C1 QA with C self-approval.

Initial C status on 2026-10-15: **design/checklist only; production script, run, actual text-layer PNG, matched CLEAN, generated DDS and game run NOT YET VERIFIED**.