# DX9Ex lens-flare review consolidation and bounded diagnostic application (2026-10-27)

- TASK_ID=LENSFLARE-REVIEW-APPLY-20261027; ACTOR=AI2 ChatGPT2; TARGET_BRANCH=vr-d3d9ex-focus; SSOT=GitHub branch HEAD.
- SOURCE_REVIEW_BASE=f398987d61ef835fe909a017b90358339d895ca3. IMPLEMENTATION_COMMITS=b38b115ea383070eb177316f505ae4530ac03c76,b8ef7ce63addbb924ac4d98b3f98f956c91f5bee,e22513f7dda81db4ddba6280f5d60799068b90cb,a439d53e7ac6099c68ba015d29d59485f14b1ac6,9f6bdcab8158dc1484e18e5f71000cc003eed8ba,c794347b45d61e685bae2274c89ed5dd505272bd.
- R26+HUD BASELINE=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 (unchanged). R84=COMPARISON_ONLY; DX11/DXVK=OUT_OF_SCOPE; no N100 or local checkout; no B9200 +5 hook.
- DELIVERABLE=read-only source-call diagnostics plus repaired destructive/static verifier contracts, NOT a headset optical workaround. GPU_VISUAL_FIX=NOT_CLAIMED; RUNTIME_VALIDATION=UNTESTED.

## What the accumulated reviews establish

| Evidence / lineage | Static conclusion | Safe decision |
| --- | --- | --- |
| 01522 and 01531; 1655, 1730 | C993/CABE transient ProjectedScreenEffect2D scope and native c64 upload/eye-route differ conditionally; C993 token None does not activate BuildProjectedSunRay. Deferred 4056D0 can outlive wrapper scope. No affected exact physical GPU Draw traced yet. | DO NOT globally force LensFlareCentre, HeadInverse, finite-depth parallax, or SceneEffect overrides. Record source admission without claiming it proves physical projection. |
| 01529, 1654, 01530 | The two source 0x570008 calls in one sun sequence have different placement/alpha; first generally queued, second immediate. Original 4056D0's opaque queue is not mod SpriteNode/D3DX queue. A source ordinal is not an eye RT Draw serial. | Preserve both original 0x570008 calls and all original visibility/alpha. Log scope, source ordinal and mod queue separately; label physical Draw unobserved. |
| 1722 and 1730 | Original opaque descriptor stores its game matrix for a later flush; the mod semantic owner can change by the physical Draw time. Matrix preservation alone does not prove correct per-eye routing. | Never patch 4052C0/405890 without game byte + descriptor provenance. Use existing R30/host telemetry for eventual join. |
| 1815 and 1938 | Legitimate original visible PMT material passes can draw twice. The write-free 0x570010 occlusion query traverses both pass draw lists and child/sibling meshes: its BEGIN/END can contain N>=0 native Draws. | Never treat multiple Draws or R26 per-Draw single-exec increments as proof of a same-eye duplicate. Do not suppress query, pass1 or the second visible 570008. |
| 1908 | R7/R26/R30 active-query guards conditionally prevent stereo replay for each eligible tracked, write-free query Draw. | Keep query and depth/write mask guards; no global stereo adjustment. |
| 01528 and lens pose 1546 | Normal R23 projection-layer count is one two-view layer; source-eye metadata can be cached across ticks. | Do not change host cached pose to live XR pose while reusing older pixel data. |
| 01532 | Original reconstructed sun source S=gameEye+direction*range is camera-relative directional, not universally a finite fixed-world object. Correct head-yaw behavior is a separate falsifier from translation disparity. | Do not demand artificial finite binocular depth; verify fresh-frame yaw against matched source/host poses before optical patch. |

## Applied implementation (no effect suppression)

1. In `tools/verify_dx9ex_r84_lens_source.py`, negative mutation now targets the R33 native two-eye owner rather than the unrelated earlier rank probe, and explicitly requires the actual negated pre-LEFT coherent original-c64 veto. This repairs a real false-negative mutation check which blocked official focus CI. Original runtime guard unchanged.
2. In `tools/verify_vr_r33_single_classification.py` and `tools/verify_vr_r33_mono_bypass_xyzrhw_fastpath.py`, require the current once-captured stateBlockRecording/stereoWanted/targetBackBuffer operands and the same fail-closed bypass. Do not reintroduce duplicate D3D9 API checks.
3. In `src/hooks_graphics.cpp`, add telemetry-gated, first-N/power-of-two sampling at existing C993/CABE source hooks only: C993 exact object ID, sequence, projected admission, mod sprite queue and ambient scope; 570008 ordinal/alpha/flags now include ambient scope and mod sprite queue. Mark `physicalDraw=UNOBSERVED`, `opaqueFlush=UNOBSERVED`. This is intentionally NOT a new 4052C0 hook and cannot establish true PMT queue mode or visible eye RT identity.
4. In `tools/verify_vr_e_flare_unhidden.py`, require the read-only source-vs-physical diagnostic labels while retaining both 0x570008 original children and native-first rival isolation.

## Visual root-cause ledger

- A extra original emitter: OPEN; two 570008 calls and multiple PMT passes are legitimate; require unexpected extra source serial and actual visible color write.
- B same-eye GPU replay: OPEN; expected normal LEFT/RIGHT and per-original-pass draws must be excluded by sourceSerial+flushID+descriptor+mesh+primitive+pass+material+texture+colourmask+eyeRT.
- C incorrect eye WVP / mixed native routes: STATIC CONDITIONAL. First queued CABE, immediate CABE and C993 may have divergent semantic or format routes. Physical shader/FVF/WVP/pose capture needed.
- D intended overlapping glow: supported by original design, HMD separation unknown.
- E host extra same-tick layer: normal pathway not supported; temporal cached-source attribution still open.
- F yaw/translation head-lock: original directional sun supports yaw test; no current Quest3 proof.

## Next source-to-eye evidence required before an optical fix

1. Reproduce in the actual Quest3/VDXR stage with telemetry enabled; collect C993/CABE source IDs/sequence/ordinal/alpha, full 4052C0 actual PMT draw/pass/texture/colour-mask if safely traceable, native R30 route/VS/FVF/c64 and physical LEFT/RIGHT RT receipt.
2. Capture host fresh versus cached source eye-pose timestamps, stable directional source sun and head yaw; do not infer head-lock solely from equal eye WVP or zero translation parallax.
3. Compare to protected known-good R26 path. Only a proven exact descriptor/flush-generation ownership loss can justify a narrow lens-specific transaction-fenced production correction. Reject broad TLS lifetime changes, arbitrary finite sun depth, altered PMT query or alpha order.

## Validation policy

- Source edits are not an HMD optical fix. CI source/gate and PC build may PASS independently; they do not prove user-visible flare has been corrected. All conditions should be checked at the exact material SHA, not on later docs-only descendants.
- Score accounting: no second point for each follow-up verifier repair, CI rerun, docs bookkeeping, or previous 01522..01532 reviews. New achievement may be scored once only after independently verified material task completion and authoritative AI_SCOREBOARD.md update.
