# OutRun 2006 HD — completion-first execution plan
Updated: 2026-11-22 KST

## Decision
User explicitly prioritizes having a complete Korean **playable test candidate** over perfect lettering QA. Do not wait for every strict C1/C3 HOLD. This does NOT authorize claiming tested gameplay or redistribution of proprietary game data.

## Input, immutable checks
- Existing 954 ROI reviewed translation crosswalk, 104 source HD DDS and SHA-verified source plan on `korean-localization-recovery-20260928`.
- Existing A/B Korean ImageGen output PNGs, reused where possible. They take priority over locally synthesized backup lettering.
- Do not change game EXE/VR/FFB, auto-browser schedule, source assets, or end user's actual install. All heavy image CPU runs on hosted GitHub Ubuntu runner, not N100.

## Target and acceptance levels
1. **COVERAGE-FIRST BUILT:** 104/104 SHA-matched source DDS processed, 954/954 reviewed ROI represented, 0 unrepresented ROI, 104 exact-hash DDS round-trips, ZIP CRC good; test-only patch produced. The original DDS format may be transformed to uncompressed RGBA32 mip1, which could be incompatible with real runtime.
2. **COPY-GAME TESTED:** An independent copied game with HD texture replacement enabled loads all needed DDS, menu/stage HUD text visibly appears, no startup crash. Evidence must come from actual user/game test, not synthetic CI.
3. **RELEASE CANDIDATE:** Only after the user accepts the test visuals and rollback behavior; strict QA background cleanup may remain imperfect.

**COVERAGE-FIRST BUILT is not equivalent to GAME TESTED or RELEASE CANDIDATE.**

## Implemented execution
- New packaged builder `tools/localization/make_hd_korean_coverage_first_package.py` validates complete 954 ROI report, the SHA-verified 104 output DDS, exact original source hashes, ZIP CRC, reversible PowerShell install, and emits `TEST_ONLY_INSTALL_MANIFEST.json` compatible with the existing installer.
- New regression suite `test_make_hd_korean_coverage_first_package.py` checks 104/954 success, missing ROI refusal, altered output ZIP refusal and DDS digest mismatch refusal.
- New workflow `.github/workflows/outrun-hd-coverage-first.yml` on `master` runs the existing hybrid fallback compositor on GitHub-hosted Ubuntu, applies A/B PNG within original geometry when possible, generates a full ZIP and QA summary.
- The installer defaults to a 5-DDS canary; `-ApplyAll` installs all 104 only with `-ConfirmTestOnly`. It validates user's original DDS sha256 and creates per-file backups and a rollback journal; `-AllowMissingSource` is an explicit separate opt-in.
- Strict 611-HOLD track continues separately. No additional browser polling intervals were changed.

## Correctness and limitation ledger
- Existing hybrid `fallback_compose` is conservative even in the relaxed lane: true overlapping glyphs use a relocation pass. A duplicate text/near-equal ROI may be represented once; mark as `duplicate_translation_represented_count`, not two new painted glyphs.
- A/B candidate images that fail alpha/transparency/size validation are not silently imported; fallback font is lower fidelity than original lettering.
- A broad ROI wipe can erase protected decorations. The resulting package MUST be labeled TEST_ONLY.
- If a rebind requires an impossible placement, script fails completion-gate; do not fake 954 coverage. Repair the exact set reported before rerunning.
- Existing compressed DDS are emitted as RGBA32 mip1 (per current hybrid source); verify in-game compatibility before claiming success.
- Never commit commercial original game DDS or full mod test packages to public source. Artifacts remain short-lived private-to-account where supported.

## Next action after automated build
- If GitHub CI FAILS, inspect named exception or `qa_report.json`; fix only the specific systemic blocker, then retry. Do not award points for the retry.
- If CI PASSES, link exact Actions run artifact containing complete test package, verify count SHA and README, ask user only to run test-copy game canary and report screenshot/crash/failure. Game runtime cannot be approved by source-level automated tests.
- Final migration from TEST_ONLY requires actual start/menu/stage/playable screenshot and explicit game-test confirmation.

## Progress counters
Treat `source_dds_verified`, `output_dds_count`, `translation_coverage_accounted`, `duplicate_translation_represented_count`, `ab_candidate_applied_count`, `fallback_hold_count`, and `release_approved` as distinct. Never add up duplicated or merely placed pixels as independently C1-validated translations.
