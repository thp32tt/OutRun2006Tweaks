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
  If queue is empty or every entry is already done, this is IDLE. It does
  **not** OCR or invent new phrase coordinates.
- Evidence: `docker_last_run.json`, `docker_run_audit.jsonl`,
  `docker_holds/*.json`; every result remains `TEST_ONLY`.
- Docker restart: `unless-stopped`; network none, cpu 0.35 and memory 512 MB.
- Deploy from this directory with `docker compose -f compose.yaml up -d`
  (N100 must have the cached `outrun-kor-c-salvage:20261015` image).
- Check: `docker logs --tail 50 outrun-c-original-english-crop`.
  No Portainer stack or existing containers are modified.
