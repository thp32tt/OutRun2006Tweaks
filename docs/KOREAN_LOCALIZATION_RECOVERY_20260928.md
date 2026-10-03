# Korean Localization Recovery Baseline — 2026-09-28

## Purpose

This branch restores the localization workflow to the last compact, working structure before later automation/controller requirements accumulated.

- Branch: `korean-localization-recovery-20260928`
- Source snapshot: `11631c5f12037bcd01cda1af57ec9bc564af4bcf`
- Snapshot time: 2026-09-28 10:12 KST
- Source branch at snapshot: `korean-localization-clean`
- Controller pair: `localization-controller-recovery-20260928`

## Frozen workflow

Only three roles are required:

- A: odd-index production + self QA
- B: even-index production + self QA
- C: cross-lane final QA + approval

The controller sends only the short A/B/C entry commands. Detailed work rules are read from `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`.

## Deliberately excluded

Do not import later complexity by default:

- queue-controller schemas added after this snapshot
- Production ID / Event ID split layers
- rollover/retry bookkeeping as production state
- C0-C6 pipeline state machines
- status-only/material-commit forcing rules beyond this baseline
- VR/DX11/DXVK/FFB controller logic
- N100 local repository as localization SSOT
- duplicated long prompts in Docker or ChatGPT Project instructions

If a later feature is needed, add it one at a time and verify that A/B production and C QA still complete real asset work.

## State authority

GitHub branch state is authoritative. Existing completed work is not repeated. Pending and REWORK_REQUIRED rows in `localization/graphics/asset_queue.csv` drive production.

Runtime/in-game validation must be reported separately when it was not actually executed.
