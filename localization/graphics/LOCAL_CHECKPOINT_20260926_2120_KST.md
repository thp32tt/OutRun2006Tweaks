# OutRun 2006 Korean Graphics Strict QA — Checkpoint

Timestamp: 2026-09-26 21:20 KST
Branch: korean-localization-clean

## Canonical source
- Original archive SHA-256: e17db462fcad129d737d385d78f0dd45a569e7640c0c8fc16f5b24e5980b1c57
- DDS inventory: 243
- Previous strict reset: 24 REWORK_REQUIRED / 8 ZOOM_MANUAL_REQUIRED / 0 PASS

## Local full32 re-scan
- The actual 32-DDS combined package was rechecked against the canonical archive.
- 28 assets were automatically flagged by coarse strict risk gates.
- 7CE1CFC5, 2DA43E41 and 53CE39D5 also require rework/manual cell-mask review.
- 37759842 remains original/unchanged.
- Historical retained/promoted status is not grandfathered.

## User-approved P0
The user visually approved:
- 571E78F3_512x64.dds
- 62BEBF33_512x64.dds
- E3FD08BE_512x64.dds

All three also pass:
- localized bbox contained inside original bbox
- changed pixels outside original bbox = 0
- introduced alpha outside original bbox = 0
- 128-byte DDS header exact match

These three are USER_APPROVED_LOCKED and must not be routinely reworked.

## Remaining P0
- EBEF6D20_512x512.dds: REWORK_REQUIRED. Localize Loading/Diverge/Left/Right with independent original text-cell masks only.
- 841E796B_512x128.dds: REWORK_REQUIRED. Preserve all vehicle/model cards; localize yellow No Handicap badge only. Prior repair attempts were rejected because of source residue or badge texture/edge damage.

## Global strict rules
- No localized glyph/outline/shadow pixels outside original approved cell.
- Localized bbox may not exceed original bbox.
- No residual English, patch seams, halos, clipping, accidental opaque boxes, or non-text edits.
- Reconstructed overlay/box must not protrude beyond the original icon/card boundary.
- Preserve brand/model/logo/song/legal/license/credit artwork.
- Final DDS must be deterministic source-based rendering/compositing, never generative artwork.
- If patch repair cannot preserve the original form, rebuild the affected element from the exact original while preserving surrounding art.
