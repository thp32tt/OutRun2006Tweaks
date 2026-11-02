# OCR-free Korean DDS v3 ink-aware overlap recovery (2026-11-02)

## Objective and constraints
Finish the 63 held ROI left by the earlier deterministic `trim` pass
without new OCR, paid ImageGen, source PNG mutation, C1/producer mutation, or
game auto-installation. User accepts lower fidelity for this isolated
**TEST_ONLY** renderer. Runtime/C1/C3 QA is not passed.

## Change
`offline_overlap_ink_resolver.py` is a second pass after existing `trim`:
- Regenerate the accepted Korean glyphs to determine their *actual compact
  ink bounds* (with 3px protective padding). Original full ROI rectangles
  are not blocked if there is only empty space around existing glyphs.
- Calculate free rectangles inside each remaining SHA-approved original
  source ROI, capped at 32 candidate fragments and eight glyph trials
  per held label, with a bounded 1600×600 rendering patch.
- Re-render each complete Korean phrase into a single free rectangle.
  Prior accepted ink pixels are asserted byte-identical.
- Treat same translated label with ROI IoU >= 0.8 as
  `DUPLICATE_TRANSLATION_REPRESENTED` instead of drawing duplicate text.
- Fail closed with `INK_AWARE_NO_READABLE_SPACE` if no safe rectangle.
  Never mark an unrendered, nonduplicate label as successful.
- Check every pixel change remains inside an approved source ROI.
  Record `ink_relocated_count`, `represented_count`, their evidence,
  and distinct output modes in SHA-verified receipts.

## N100 executed tests
- Original v2 reports: 104 full DDS candidates; 891 drawn translations +
  63 held overlaps among 23 source variant PNGs.
- **All 23 held source variants rebuilt on real full-HD input** (sha-verified);
  ink-aware pass placed **59** complete Korean strings, exactly **four**
  overlapping identical-text ROIs were already represented, and no holds
  remain.
- v3 combined deliverable: 104 DDS (23 newly rendered + 81 unchanged,
  SHA-digest-cache checked zero-hold v2 outputs reused as hardlinks to
  avoid CPU/disk load), 104 QA receipts, ZIP CRC pass and no unsafe names.
- Final receipts: **950 actual painted labels + 4 duplicate representations
  = 954 approved ROI accounted for**; 321 earlier trim relayouts included.
  0 held, 0 outside-approved-ROI pixels changed, 0 DDS PNG roundtrip
  mismatches, 0 original source modifications in receipts.
- N100 Python regression suite: 13/13 PASS.
  `python3 -m py_compile`: PASS;
  `bash -n entrypoint.sh`: PASS;
  `docker compose -f docker-compose.yml config --quiet`: PASS.
- v3 ZIP:
  `/home/chatgpt-runner2/work/image-src/text_roi_batches/offline_overlap_v3_ink_test_only/OUTRUN_OFFLINE_KOREAN_TEST_ONLY_96e9372fb718.zip`
  (140,069,153 bytes; SHA-256:
  `84d92c22ff957ebeaa3156165b9ed7ef769802756ddc183d18bd586ff5c1ddf3`).
- All generated tests/output marked `TEST_ONLY_NOT_RUNTIME_APPROVED`,
  not a game executable/runtime PASS. Original v2 ZIP retained untouched.
  Hardlinked v2/v3 unchanged DDS files share an inode: do NOT edit these
  individual candidate DDS in place; use packaged independent ZIP instead.

## Automated deployment (user-managed)
- Branch: `localization-controller-recovery-20260928`
- Compose path: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`
- `OUTRUN_OFFLINE_FALLBACK_OVERLAP_MODE=ink`
- `OUTRUN_OFFLINE_FALLBACK_OUTPUT_ROOT=/data/imagegen/text_roi_batches/offline_overlap_v3_ink_test_only`
- Existing `nice -n 15`, one source per 60s, 900s bounded worker and
  idempotent per-source SHA/report verification retained. New Dockerfile
  copies both original trim and ink-aware modules.
- GitHub push does not deploy/restart containers; the user handles
  Portainer Git pull, Rebuild, Redeploy, with volumes preserved.
- Existing v3 files were generated on N100 independently and will be
  recognized as `ALREADY_VERIFIED` by the new worker.

## Remaining risks
This 2nd pass may leave old English lettering outside the chosen
sub-rectangle inside a broad approved ROI. Some visual elements inside
approved ROIs can be damaged or translated lettering shifted. DDS uses
uncompressed RGBA32 with one mip level and can increase VRAM. Actual
game/VR visuals, font size, menu line wraps, protected-art appearance,
C1/C3 independent inspection and live gameplay performance remain untested.