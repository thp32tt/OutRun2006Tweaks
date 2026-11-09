# OutRun 2006 HD localization HOLD: source-bound recovery (2026-11-10 KST)

## What is verified (NOT a game release)
- Source: exact GitHub multi-atlas run [42483996468](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/42483996468), source asset SHA `d8f90f6e64fa61f33739d6304328d1d4f4018362`; 954 imported ROI, 300 mechanically assembled into 58 native DDS, 654 HOLD.
- Native DDS original SHA conflicts = 0, original DDS unavailable = 0. All output stays TEST_ONLY / runtime UNTESTED / release NOT approved.
- Actual ROI HOLD breakdown: overlap-owner ambiguous 463; ROI source-edge crossings 95; oversized/coarse source bounds 36; source alpha/background non-isolation 37; BC3 original-format mip chain 13; BC3 translated palette loss 4; too-small/downsample glyph 4+2.
- The crosswalk contains 954 rows across 104 source DDS targets. Raw rectangular metadata generates 1,465 intersecting ROI pairs involving 714 rows BEFORE source-alpha ownership proof. This is a geometric diagnostic, **not** evidence that 1,465 pairs conflict at the ink level. The 463 remaining overlap HOLD is the audited post-proof count. Do not unilaterally trim, clear a full rectangle, or count a printed word as source-clean PASS.

## Fixed routing and tests
1. `tools/localization/hd_rework_queue.py` now routes `QA_SOURCE_NOT_ISOLATED_ALPHA_TEXT`, `QA_SOURCE_LINE_LAYOUT_UNVERIFIED` and `OPAQUE_PROTECTED_ART_HOLD` to `SOURCE_CLEAN_MASK_OR_SEGMENTATION_HOLD`, NOT to text-only ImageGen regeneration. For this exact report, the routing should become: 594 `ENGINE_OR_COORDINATE_HOLD`, 37 `SOURCE_CLEAN_MASK_OR_SEGMENTATION_HOLD`, 17 `EVIDENCE_REVIEW_HOLD`, 6 `AB_IMAGE_AND_CLEAN_REWORK`. Total remains 654 until a new candidate and independent strict DDS QA pass.
2. A/B result queue had eight current `AB_SENT` tasks (Big Forest, NEXT MISSION, Slipstream To Score!, Race The Rivals!, TimeAttack Mode OutRun2, HeartAttack Mode OutRun2, Steering Wheel :, Don't crash!) with no image PNG proven in the GitHub fallback queue receipts; do not resend or claim generated. Remote receipt diagnostics include `ASSISTANT_GENERATED_IMAGE_NOT_RENDERED_A0_G0_U1_L0`, meaning a bound user message was visible but no assistant media was present in that browser DOM snapshot.
3. `tools/chat-controller/localization-recovery-v1/github_chat_rework_controller.py` now rehydrates SHA-pinned in-flight `AB_SENT`, `C1_READY`, `C1_SENT` remote states on worker startup (at most 128 entries), preserving login/chat link verification and local checkpoints; it NEVER resubmits ImageGen as part of recovery.
4. The isolated controller CI `.github/workflows/outrun-hd-chat-rework-ci.yml` includes the assistant image rescue module in sparse checkout and checks the current persistent browser-profile contract. Synthetic verification succeeded in GitHub run [42655767279](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/42655767279); asset routing tests succeeded [42655362346](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/42655362346).

## Priority for actually reducing HOLD
- **463 overlap:** In existing `hd_overlap_ownership.py`, keep exclusive source-alpha 8-connected components and require every component be uniquely anchored to one verified source ROI. For ambiguous shared ink, gather per-glyph source mask/PSD or correct pinned source ROI; do not reflow into a different sprite cell or clear unrelated source.
- **95 boundary:** use native HD original DDS SHA to remeasure exact alpha-inclusive glyph extent (including shadow); generate a reviewed new coordinate binding, not just pad a Korean PNG.
- **36 coarse:** split verified source text and protected art into individual ROI definitions, retain original family and variant identifiers, and rerun independent ownership tests.
- **37 mixed alpha:** obtain source-owned CLEAN plate / source text-only mask, prove all English pixels removed and background/sprites identical before admitting any new Korean PNG; a new glyph image alone cannot fix this.
- **17 BC3:** retain original DXT5 format, mip levels, original palette/index protection and decoded protected-pixel identity. Do not replace with uncompressed one-mip fallback in a distributable build.
- **6 glyph scale:** use existing A/B PNG and deterministic lossless alpha padding/refitting first; regenerate only the proven missing glyph/effect component, then C1 independent review.

## Gates
- Re-run exact-SHA GitHub native DDS production and compare strict reports and byte-identical deterministic dual builds. C1 independent QA, C3 strict visual and real game validation remain outstanding.
- N100 Docker is a browser/upload/download and SHA receipt bridge only; GitHub-hosted Actions carries DDS and image QA CPU work. No paid API, no unattended game release, no fake approval.
