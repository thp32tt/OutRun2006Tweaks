# N100 OutRun C — original English crop only

This is a **standalone Docker Compose project**. It never restarts the paused
OutRun A/B/C1 controller, never runs ChatGPT/ImageGen, Korean generation,
CLEAN, DDS modification, or VR services. No external network or exposed ports.

- Source: SHA-pinned full original HD PNG under
  `work/c_salvage_text_roi/source_full_20261012`; image mount **read-only**.
- Provenance: `c_crop_only_runner.check_original()` verifies exact source DDS SHA,\n  complete native DDS decode, source PNG SHA, native dimensions, and full pixel equality.\n  Additional DDS sources are admitted only by SHA/pixel-verified source inventory.
- Input queue: `work/c_salvage_text_roi/c_original_hd_crop_only/queue_specs/*.json`.
  Each spec has exactly one complete phrase, original-source SHA + DDS SHA
  and exact reviewed bbox; use schema `outrun-c-n100-hd-original-crop-v1`.
- Output: `.../c_original_hd_crop_only/outputs/<queue>-<id>/`
  with pixel-exact `english_original_native_crop.png` and `crop_manifest.json`.
- Guard: 255 archived crops are immutable, matching archived queue + XYXY
  is skipped, old output never overwritten, no source tiles accepted.
- Schedule: 60 seconds per poll, up to 10 *new verified queued* crops/cycle.
  The worker runs bounded English OCR batches once per 60-second poll; each\n  batch rotates through up to four verified complete HD sources. The\n  checkpoint `auto_discovery/ocr_source_cursor.json` preserves progress.
- Automatic geometry discovery: non-destructive alpha/connected-component
  analysis proposes possible text bboxes in `auto_discovery/Q*_candidates.json`.
  Each proposal is deduplicated against the 255 archived native crops and the
  queue. Alpha-only candidates are diagnostic HOLD; Tesseract OCR is now\n  installed separately and is the active production detector.
- Autonomous acceptance of prior-reviewed isolated English rectangles:
  `reviewed_regions.json` supplies exact text, tested original pixel provenance
  and reviewed bbox. `discover.py` checks those against the official original
  English transcription before atomically enqueuing each NEW approved bbox.
  The normal native crop worker then runs the next minute; unknowns are not
  falsely promoted to finished English crops.
- Smoke test (2026-10-17): 2 pinned DDS sources verified, 11 candidates on
  review HOLD, 1 newly enqueued and actually cropped as TEST_ONLY:
  Q060 `IN...` (310x105 pixels) with source/crop SHA manifest.
- Existing HD sources already on N100 are admitted with\n  `admit_existing_hd_originals_20261017.py`, which matches the exact official\n  original DDS paths in the project's `transcriptions.jsonl`. It prioritizes\n  the pinned canonical `localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a`\n  and then the previously archived `binary_compare/original/*.zip` original DDS.\n  The original comparison ZIP contains 79 DDS: **39 actual 4x native HD** and\n  40 standard-resolution variants, which are excluded. The canonical source\n  directory contains 18 original full DDS. Their union covers **49 unique\n  transcribed native-HD source groups** (plus separately pinned Q212).\n  Staged records are in `docker/source_registry_auto.json`; source PNG + DDS\n  full pixel equality is mandatory before the OCR worker reads new files.\n  No prior 986 tile or reassembled images are ever eligible.
- Evidence: `docker_last_run.json`, `docker_run_audit.jsonl`,
  `docker_holds/*.json`; every result remains `TEST_ONLY`.
- OCR engine: Tesseract 5 with English traineddata bundled in a dedicated
  `outrun-c-english-ocr:20261017` image (built via `Dockerfile.ocr`).
  OCR runs locally/offline on small rotating source batches and takes
  the 16+ reviewed English transcriptions as a strict phrase allowlist.
  `ocr_recognize.py` automatically accepts only high-confidence exact English
  matches, outside the 255/archive/queue, with non-clipped native bbox and
  independently verified full DDS/PNG source; it atomically enqueues them.
  Every OCR crop still receives TEST_ONLY and no runtime PASS.
- Verified-source coverage expanded: Q051, Q060, Q116, Q161, Q197,
  Q212 (6 unique original DDS/PNG pairs). Each source is pinned by SHA256,
  dimensions, and full decoded DDS pixel equality including FLIPY orientation.
  Q116/Q161 compressed DDS is decoded natively by Pillow, not resized.
  The four extra verified source PNGs and DDS files are staged only in N100's
  C-approved original directory; generated/reassembled tiles are not used.
  Other source groups remain HOLD until their genuine original is verified.
- OCR remains fallible: items with source/letter ambiguity, wrong/incomplete
  text, clipped alpha/effect or non-text sprites are rejected or HOLD, never
  guessed to force production. See `auto_discovery/Q*_ocr_results.json`.
- Predeployment OCR probe: Q051/Q060 genuine DDS verified, 9 official phrase
  matches, 8 already cropped excluded, 1 border-overlap held, 0 new queues.
  The older manually reviewed `IN...` smoke crop is separate from OCR.
- Docker restart: `unless-stopped`; network none, cpu 0.35 and memory 768 MB.
- Deploy from this directory with `docker compose -f compose.yaml up -d`
  (N100 must have the locally built `outrun-c-english-ocr:20261017` image).
- Check: `docker logs --tail 50 outrun-c-original-english-crop`.
  No Portainer stack or existing containers are modified.
**2026-10-17 performance policy:** the older alpha-only geometry candidate sweep is
retained for offline diagnostics but no longer runs periodically in production.
Tesseract supplies phrase text and native coordinates in the same bounded pass.
2026-10-17 validation: the C worker processed new Q044 and Q047 original HD\nsource records, OCR automatically queued 10 previously unknown English ROIs,\nand emitted new TEST_ONLY native PNG crops with verified SHA. There is no\nimplicit game/runtime PASS, and historic 255 crops remain unchanged.\n

## Full unsplit original HD PNG 108 — 2026-10-17

- **Source of truth:** ChatGPT Library original assets under
  `아웃런 한글화 이미지/2026-10-13_HD원본_PNG_수동번역`.
  Five original ZIPs were copied to the connected private Google Drive folder
  `OutRun_N100_TRANSFER_20261014` only for transfer, then downloaded to N100.
  The old Google Drive content had only the legacy tile ZIPs.
- On N100 the original ZIPs are at `hd_original_108_zip_inbox/`, total 5 ZIP.
  All five ZIP SHA256 digests match the original Library ZIP hashes.
  `import_hd108_zip_inbox.py` extracted and independently SHA-verified all
  108 unique **unsplit** PNGs against `01_DDS_PNG_MANIFEST_108.csv`.
  The 108 original files are in `hd_original_108_verified/`.
  Import receipt is `hd108_import_receipt.json`: 108/108 SHA/dimensions PASS.
- **Offline automation:** `docker/ocr_hd108.py` processes the 108 source PNGs,
  two at a time, before the older 50-source DDS OCR pass. It cross-checks each
  PNG's original SHA before OCR, allows only official reviewed English phrases,
  enforces overlap and clipped-alpha holds, outputs pixel-exact native RGBA
  crops to `hd108_outputs/`, and records `TEST_ONLY_UNTESTED_IN_GAME`.
  Progress is in `hd108_ocr/cursor.json` and `hd108_ocr/last_scan.json`.
- These 108 source PNGs have their **original DDS path and SHA** in the
  library manifest; **DDS pixel equality is not independently proven** for
  assets not available as original DDS. Do not describe those results as
  DDS-pixel-verified. The original DDS verification pipeline stays separate.
- No historic 986 split tiles, AI-generated output, background cleanup,
  Korean replacement, DDS composition, VR, or A/B changes.
- Docker redeployed with Tesseract OCR and `unless-stopped`; source-side
  initial two-item OCR smoke returned scanned=2, held=0, new_crops=0.
  Processing additional source PNGs is asynchronous and not claimed complete.
