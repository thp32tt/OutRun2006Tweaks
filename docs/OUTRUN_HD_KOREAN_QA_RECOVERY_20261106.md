# OutRun 2006 HD Korean QA recovery plan — 2026-11-06 KST

## Source of truth and measured baseline

- GitHub assets: `thp32tt/OutRun2006Tweaks@korean-localization-recovery-20260928`.
- QA evidence: `korean-localization-qa-queue-20261104:localization/automation_runs/hd_rework_queue/{latest.json,last_report.json}`; compare **QA source ZIP SHA**, not just a scheduled workflow success.
- Source list: 954 active ROI, A/B original high-quality PNG imported for 954/954, pending import 0. Original native DDS sources SHA-pinned for 104/104 (historical verified source inventory).
- Last strictly reported **TEST_ONLY**: 250 translated ROI composed into 46 DDS atlases, of which 245 used deterministic existing-pixel salvage; 704 ROI held. These are **not** 250 C1/C3 PASS and **not** a usable game release.
- Hold accounting: overlap 457; unsupported DDS original format/mip 111; source ROI edge 80; coarse box contains other text 30; isolated source alpha unproven 21; downscale lost glyphs 3; too-small text 2. Sum=704.
- `release_approved=false`, `runtime_validation=UNTESTED`, C1 preliminary new PNG 0. Keep all until independent visual and actual game evidence.

## Execution order — no new ImageGen / no generic font

1. **Exact-source overlap discrimination (implemented 2026-11-06).** In `tools/localization/hd_strict_qa.py`, distinguish intersecting broad ROI rectangles from truly *shared original alpha pixels*. Only allow overlapping metadata regions if their shared intersection has **zero actual source alpha pixels**, then preflight the resampled translated alpha against **every other active non-coarse ROI**, including not-yet-processed rows. Reject ANY resulting translated pixel intrusion. Add synthetic tests for: empty shared source padding may pass; translated overlap still HOLD; shared alpha stays HOLD. No alpha boundary or source pixels are guessed.
2. **Trigger GitHub-run source-bound DDS QA** from changed engine/test code. Keep GitHub-hosted Python execution, two deterministically identical DDS/QA ZIP builds, protected-pixel and original-header checks. Do not claim success or a positive delta until the exact run and its published `last_report.json` SHA are confirmed; canceled or pending runs count zero.
3. **Fix format/mip cluster (111 ROI) separately.** Inspect each pinned original DDS header/pixel layout and mip hierarchy; implement original-format-preserving encode/decode + matching dimension/format/mip roundtrip tests **only with evidence**. Never convert BC/mip textures to arbitrary uncompressed BGRA or pretend unsupported DDS is passed.
4. **Fix coordinate/mask cluster** after geometry test: source-edge 80, coarse 30, ambiguous isolated alpha 21. Require proof that surrounding pixels are clear or source-reviewed CLEAN/mask; never rectangle-clear unknown background or HUD artwork. Reuse 954 saved A/B PNG, never re-run ImageGen for an engine/mapping error.
5. **Handle 26 genuine A/B image/CLEAN failures** only after engine and coordinate holds have been separated. Reuse, pad, reflow or downscale existing PNG where safe; leave unsalvageable pixels as HOLD. Any new ImageGen requires explicit per-ROI evidence in the separate original ChatGPT production lane, not a GitHub Actions API or font fallback.
6. **Independent QA and release.** C1/C3 inspect source/CLEAN/final per atlas, actual Korean text, slant, two-line layout, native+50% readability, game UI neighbors, FLIP-Y/RAW and protected art. Then user independently verifies game. Never auto-install TEST_ONLY or mark `RUNTIME_VALIDATION` as PASS from automated image metrics.

## Machine-verifiable acceptance contract

- `active_roi_total == translated_roi_generated + sum(hold_roi_reason_counts.values()) == 954`.
- No original DDS SHA conflicts, no missing A/B PNG, no unsafe symlinks or non-source text fallbacks.
- Preserve original DDS format, exact header, dimensions, orientation and mips. Save preview and native DDS only when roundtrip and protected-art checks pass.
- Every previously held ROI can become TEST_ONLY only with source and translated pixel-level proof. No source-pixel-shared overlap may be auto-promoted.
- Compare exact GitHub Actions run ID, commit SHA, QA artifact SHA, before/after HOLD breakdown; changed code alone is not improvement evidence.
- N100 is a low-impact controller/checkpoint only. Intensive DDS processing runs on GitHub Actions CPU, no Docker on GitHub; no N100-heavy builds or repeated uploads.
- Review production versus release as separate tracks: UI localization completion is not established while any hard HOLD or in-game failure remains.

## 2026-11-06 work ledger

- `059f326bf924e2782e31620756812ebc742a6881` — pixel-proven ROI overlap and translated-ink protected-box preflight.
- `2ad912267fdc1e987fd0e24fa833ee358bb67c99` — two synthetic regression tests; existing shared-ink HOLD test retained.
- At writing, the newer GitHub multi-atlas workflow was pending. Its outcome and delta must be retrieved from GitHub, never presumed.
