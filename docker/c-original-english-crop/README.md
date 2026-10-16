# N100 OutRun C — original English crop only

This is a **standalone Docker Compose project**. It never restarts the paused
OutRun A/B/C1 controller, never runs ChatGPT/ImageGen, Korean generation,
CLEAN, DDS modification, or VR services. No external network or exposed ports.

- Source: SHA-pinned full original HD PNG under
  `work/c_salvage_text_roi/source_full_20261012`; image mount **read-only**.
- Provenance: the existing `c_crop_only_runner.check_original()` verifies
  registry identity, native original DDS bytes and full PNG pixel equality.
  New originals require independent review and a verified allowlist change.
- Input queue: `work/c_salvage_text_roi/c_original_hd_crop_only/queue_specs/*.json`.
  Each spec has exactly one complete phrase, original-source SHA + DDS SHA
  and exact reviewed bbox; use schema `outrun-c-n100-hd-original-crop-v1`.
- Output: `.../c_original_hd_crop_only/outputs/<queue>-<id>/`
  with pixel-exact `english_original_native_crop.png` and `crop_manifest.json`.
- Guard: 255 archived crops are immutable, matching archived queue + XYXY
  is skipped, old output never overwritten, no source tiles accepted.
- Schedule: 60 seconds per poll, up to 10 *new verified queued* crops/cycle.
  Every 600 seconds, the same worker runs `discover.py` over the SHA- and
  DDS-pixel-proven verified source registry (currently Q051 and Q060).
- Automatic geometry discovery: non-destructive alpha/connected-component
  analysis proposes possible text bboxes in `auto_discovery/Q*_candidates.json`.
  Each proposal is deduplicated against the 255 archived native crops and the
  queue. **No OCR is installed; automatic candidates have no validated English
  text, may contain non-text artwork, and remain HOLD until visual review.**
- Autonomous acceptance of prior-reviewed isolated English rectangles:
  `reviewed_regions.json` supplies exact text, tested original pixel provenance
  and reviewed bbox. `discover.py` checks those against the official original
  English transcription before atomically enqueuing each NEW approved bbox.
  The normal native crop worker then runs the next minute; unknowns are not
  falsely promoted to finished English crops.
- Smoke test (2026-10-17): 2 pinned DDS sources verified, 11 candidates on
  review HOLD, 1 newly enqueued and actually cropped as TEST_ONLY:
  Q060 `IN...` (310x105 pixels) with source/crop SHA manifest.
- To scale beyond Q051/Q060, obtain and independently prove each genuine
  complete original DDS and full PNG before adding to source allowlist.
  No legacy 986 tile or reassembly is eligible.
- Evidence: `docker_last_run.json`, `docker_run_audit.jsonl`,
  `docker_holds/*.json`; every result remains `TEST_ONLY`.
- OCR engine: Tesseract 5 with English traineddata bundled in a dedicated
  `outrun-c-english-ocr:20261017` image (built via `Dockerfile.ocr`).
  OCR runs locally/offline in the C container every 600 seconds and takes
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