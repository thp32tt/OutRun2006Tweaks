# 2026-11-02 OCR-free local Hangul fallback (TEST_ONLY)

## Rationale
All current approved A/B ImageGen ordinals have been consumed, whereas GPT OCR repeatedly returned NO_VALID_DETECTIONS / REVIEW_REQUIRED. The user's explicit lower-fidelity authorization allows a bounded, *reversible* fallback that uses already SHA-verified source PNG, immutable reviewed translations, and approved bounding boxes. This path never calls OCR, ImageGen or a paid API.

## Implementation
`offline_korean_sprite_fallback.py` reads `work/image-src/text_roi_batches/production_manifest.json`, opens the exact SHA-bound full-HD RGBA PNG and exact corresponding canonical DDS, byte-verifies native pixels (including FLIP-Y), then renders Hangul with local Pillow/Nanum/Noto and a minimal outline. It erases pixels *only within registered ROIs* and holds opaque regions, overlaps and ambiguous DDS pins. It writes a new `KOREAN_READABLE_TEST_ONLY.png`, a single-mip 32-bit `KOREAN_NATIVE_TEST_ONLY.dds`, and a SHA receipt into a separate output folder. No source DDS, A/B/C1 state, queue or source PNG is modified. This deliberately trades original lettering effects for throughput; original pixels inside the edited ROI may lose art/background and require visual review.

Usage on N100:
```bash
python3 tools/chat-controller/localization-recovery-v1/offline_korean_sprite_fallback.py \
  --source-name Q054_FA7BBB13_BASE_READABLE_FLIPY.png --max-rows 7 --execute
```
Same with `Q044_19CEDB9_BASE_READABLE_FLIPY.png`.

## Actual live original-file tests on N100
- Q044 original SHA256 `fd42d6909b5275979e63e793ec2744a672929f0dbca7b759c62a5da4d76a6d4e`, original DDS SHA256 `2472c7aab0751987bd736131b8b4c22be4a7613d9bd1478c9b9f35a615dd6c7e`, 7 replacements, DDS roundtrip pixel equality PASS, changed pixels outside approved ROIs 0. TEST_ONLY DDS SHA256 `4a6b36daf537879937912331521b14f1334e0e131013b7828d4d2c48edb2dc65`.
- Q054 original SHA256 `70d581cf5d0a70b2dd0036d61a51110ba1e3fc39b9088c3bc5cdd3847ea7943b`, original DDS SHA256 `61c82072fcc44e9e5f4c6f127d2a29b17abecf5cdb536a5609512246d1ab8d15`, 6 replacements (one overlapping ROI skipped), DDS roundtrip pixel equality PASS, changed pixels outside approved ROIs 0. v2 TEST_ONLY DDS SHA256 `afaa8e2e3579c6fd0c2c778efd79ce09e5197e77479ecd278637992f35fdfa5a`.

## Ready-to-test N100 package
`/home/chatgpt-runner2/work/OUTRUN_OFFLINE_KOREAN_FAST_TEST_20261102.zip`, 8,222,392 bytes, SHA256 `ef4c63b5271be9671c5f4540329614e9895d4140e6ca17f6b4e602871bd397bb`. Archive verified with exactly three entries (README plus two DDS files under the HD load texture path). Extract only into an **existing matching HD UI mod after backing up those two DDS**; never overwrite original game or other graphics mods blindly.

**Not yet done:** full atlas completeness, C1/C3, texture-neighbor overlap verification, live game runtime acceptance, repeated/automated deployment, full-game release. `RUNTIME_VALIDATION=UNTESTED`.

Existing automation and OCR history remain unchanged; this is an alternate test build path, not permission to mark DDS production PASS.

## Same-task expansion: V2 additional Q057 test, no new score (+0)
Q057 full source original SHA `81f7f109be08d26f1cda6658b083cf71ec385584126b25a877f69057df199fbf`, matching native DDS SHA `2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481`; six SHA-pinned approved ROI labels were rendered (Target, Hearts, Total Rank×3, Collect the stars!), source pixels outside the approved boxes were unchanged, and the resulting D3D9 native DDS decoder roundtrip was byte-exact. Q057 TEST_ONLY DDS SHA256 `e53e7a2206bc0ac50bb261491fc298415db40d3fa1731a1012f213e9fb61f6a1`.

The updated three-DDS sample package is `/home/chatgpt-runner2/work/OUTRUN_OFFLINE_KOREAN_FAST_TEST_20261102_V2.zip` (12,829,850 bytes, SHA256 `ef32a24b7e99f0d724a90b48fa4e22813fcab2aefae045c8fa622b07fe7b1cc1`). It contains a Korean README and Q044 / Q054 / Q057 DDS in their relative HD GUI texture/load paths, total **19 ROI labels**. This V2 is the preferred test package; V1 was retained unchanged. As before, all content is TEST_ONLY and must not be installed blindly.

Q047 remains HOLD due to a different canonical DDS SHA than the N100 DDS copy in the fallback source directory. Q053 remains HOLD because its original is DXT5 with 13 mip levels; the fallback only serializes original-format, single-mip uncompressed 32-bit DDS and refuses lossy/unsupported conversions. No unsupported codec bypass was attempted.
