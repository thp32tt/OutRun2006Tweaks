# OCR-free Korean localization bulk TEST_ONLY worker — 2026-11-02

## Intent and strict safety gate
The user authorized a low-fidelity fallback for remaining OutRun 2006 graphics and explicitly reserved **manual Portainer deployment**. The fallback does not invoke OCR, ImageGen, any paid API, or overwrite existing source, installed DDS, game, browser session, A/B/C1 queue or VR code. All outputs remain `TEST_ONLY_NOT_RUNTIME_APPROVED`. Source/translation information is the SHA-pinned production manifest, not a blind OCR guess.

## Snapshot before user's next redeploy
N100 source inventory (2026-11-02 KST): 108 verified source PNGs, 954 active production rows (1,002 manifest entries including 48 retired A→B rebalance rows). Strict per-console DDS-path matching yields **104 eligible source PNGs**, **2 exact-byte variant aliases** (reuse BASE texture), **2 sources with no approved ROI** (Q143, Q152). At the end of this work **3 bulk outputs** exist (Q012, Q047, Q053), leaving **101 eligible source PNGs to process**. This is source-level tracking, **not 954/954 Korean phrases completed or game-ready**.

Successful actual N100 executions:
- Q012: 1 label, original canonical DDS not available in pinned N100 folder; derived an uncompressed DDS from exact source PNG. DDS top-level re-decode PASS, outside-ROI changes 0.
- Q047: 13 labels, canonical DDS SHA differs from the copy in pinned N100 folder; derived DDS from exact source PNG (never claimed source DDS equivalence). DDS top-level re-decode PASS, outside-ROI changes 0.
- Q053: original canonical DDS DXT5/13 mips verified. 8 approved non-overlapping labels converted to a valid uncompressed RGBA32 mip1 DDS, DDS top-level re-decode PASS, outside-ROI changes 0; 5 overlapping ROI candidates remain held for separate review.

Bulk proof ZIP (partial, only 3 verified DDS) on N100:
`/home/chatgpt-runner2/work/image-src/text_roi_batches/offline_bulk_test_only/OUTRUN_OFFLINE_KOREAN_PARTIAL_TEST_ONLY_ad37b2447de0.zip`
SHA256 `b6fa434c32fec7f72c879824b9016ee6ac223a7ae875e2173c4ad2c0548572ec` (3 DDS, 22 labels, 6,767,963 bytes). This is independent of the earlier Q044/Q054/Q057 V2 sample ZIP.

## Deployment and settings
**Only the user** performs Portainer **Pull latest + Rebuild + Redeploy** of the existing single `outrun-kor` Git Stack:
- repository `thp32tt/OutRun2006Tweaks`
- branch `localization-controller-recovery-20260928`
- Compose `tools/chat-controller/localization-recovery-v1/docker-compose.yml`.

No second container, no destructive volume recreation, no modification to other stacks. Dockerfile installs `fonts-nanum` and includes `offline_korean_sprite_fallback.py`, `offline_korean_batch.py`, and `offline_korean_packager.py`. The existing A/B/C1 tabs are retained.

Compose sets `OUTRUN_OFFLINE_FALLBACK_ENABLED=true`, `OUTRUN_OFFLINE_FALLBACK_MAX_SOURCES_PER_CYCLE=1`, `OUTRUN_OFFLINE_FALLBACK_INTERVAL_SECONDS=60`, `OUTRUN_OFFLINE_FALLBACK_MIPS=1`. `entrypoint.sh` starts a **nice 15** capped subprocess for 1 SHA-pinned source at a time. Existing reported sources are checked without regeneration; failed sources are recorded in `holds/` and do not starve the remaining queue. To retry a resolved HOLD manually, use `--retry-holds` for the same source after fixing evidence.

New files appear in shared N100 mount:
`/home/chatgpt-runner2/work/image-src/text_roi_batches/offline_bulk_test_only/`
- `sources/<PNG-stem>_<sourceSHA12>/KOREAN_TEST_ONLY.dds`
- `sources/<...>/KOREAN_READABLE_TEST_ONLY.png`
- `sources/<...>/report.json`
- `source_digest_cache.json`, `last_run.json`, `holds/<...>.json`
- once all eligible sources are processed, one content-addressed `OUTRUN_OFFLINE_KOREAN_TEST_ONLY_<SHA>.zip` with matching `textures/load/...` relative paths and QA receipts.

To inspect without mutating outputs:
```bash
python tools/chat-controller/localization-recovery-v1/offline_korean_batch.py --inventory-only
```

To test just one source without waiting for the Docker worker:
```bash
python tools/chat-controller/localization-recovery-v1/offline_korean_batch.py --only-source Q053_568D3696_BASE_READABLE_FLIPY.png --max-sources 1
```

To manually package a few already saved files without pretending it is complete:
```bash
python tools/chat-controller/localization-recovery-v1/offline_korean_packager.py --allow-partial
```

## Boundaries still OPEN
- Outputs preserve confirmed source ROI **outside** pixels exactly, but **inside** the ROI may lose protected artwork or original effects. Simpler typefaces and approximate outlines are explicitly intentional.
- DXT5 inputs are *not* recompressed to DXT5. The new DDS is RGB32/RGBA32, single mip by default; higher VRAM consumption and in-game compatibility/performance are unverified.
- Q143/Q152 do not have approved geometric ROIs and cannot be silently "completed." Several other sources have overlapping/uncertain boxes; each held region is reported rather than invented.
- Console-specific source variants without a matching DDS path are never blindly written over an unrelated texture.
- C1/C3, installed HD-mod compatibility, final DDS validation, actual game/Quest VR and screenshot signoff remain `UNTESTED`. No automatic game deployment.

## Tests
Executed 5/5 `tests/test_offline_korean_batch.py` on N100: native DDS orientation, up to three mip levels, ROI outside-pixel protection, overlap HOLD, and target-path safety. N100 live source Q012/Q047/Q053 operations succeeded. GitHub CI workflow now includes the same tests and entrypoint `bash -n`; a GitHub build/redeploy or CI success must not be assumed until verified.
