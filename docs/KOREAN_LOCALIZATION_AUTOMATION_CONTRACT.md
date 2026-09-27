# Korean Localization Automation Contract

This is the canonical contract for the N100 A/B/C localization controller. Every run MUST read this file first, then docs/KOREAN_LOCALIZATION.md, localization/WORKLOG.md, localization/progress.json, localization/resume_state.json, localization/graphics/README.md and localization/graphics/ORIENTATION_POLICY.md. Repository state on korean-localization-clean is the only work state; do not use GPT Library as a work store.

## Isolation and source rules
- Work only on korean-localization-clean. Never merge VR/FFB source or history.
- Preserve the independent original-mod Korean patch architecture.
- When an HD-mod DDS exists it is the graphics baseline. Never upscale an older low-resolution Korean DDS.
- Read DDS headers and preserve dimensions, format/compression, alpha and mip behavior.
- Preserve raw DDS per-sprite mirror/rotation/orientation.
- Preserve vehicle/model names, brands/logos, song titles/credits and legal/licensing marks unless explicitly approved otherwise.
- Preserve non-text artwork/background wherever possible and modify only intended text regions.
- Preserve source style: fill/gradient, outline, shadow/glow, proportions, alignment, scale and spacing.
- Reject seams, black lines, erasure residue, opaque boxes, alpha halos, clipping, overlap and unintended artwork changes.

## Zero-pixel-overflow rule
All new, modified and previously approved graphics are subject to exhaustive containment QA.
For each text element determine the original/HD baseline's actual non-transparent text-pixel bounding box and the applicable sprite-cell/text-region boundary. Compare the localized non-transparent pixels including outline, shadow, glow and alpha fringe.
If the localized result extends even 1 pixel farther than the original permitted text bounding box or crosses the sprite-cell/text-region boundary on left, right, top or bottom, it is FAIL and MUST be reworked. Same DDS canvas dimensions alone never constitute a pass.
Rework by reducing horizontal/overall scale, repositioning, shortening the Korean wording, or preserving the original when necessary. Recheck raw DDS orientation and readable/game orientation.
Existing approved_dds are not grandfathered: recheck them and remove/rework any FAIL.
Machine-readable QA must record per asset/element: original_bbox, localized_bbox, delta_left, delta_right, delta_top, delta_bottom, containment PASS/FAIL, and rework status.

## Three-stage schedule
- A (:00): production. Resume unfinished work, create/fix localization, run containment QA on touched assets, rework failures in the same run.
- B (:20): exhaustive QA + rework. Review A output and existing approval candidates, perform the zero-pixel-overflow checks, and immediately correct failures.
- C (:40): final QA + approval + Git synchronization. Revalidate A/B and approval candidates. Only PASS results enter/remain approved. Update state/worklog/reports and commit/push the actual changes.

## State and completion
Do not repeat completed work. Resume from current Git progress/resume state. Each completed batch updates its machine-readable report, localization/WORKLOG.md and localization/progress/STATUS.md as applicable.
Before approval inspect raw DDS and readable/game orientation; use in-game screenshot validation when available.
Git synchronization is mandatory at the end of each role when that role changed files: commit/push only its localization changes to korean-localization-clean and verify the resulting commit SHA. Do not create empty commits. Resolve conflicts by preserving current localization work and never importing VR/FFB changes.
