# LENSFLARE-MATERIAL-ALPHA-SPLIT-20261028-0528 — two original material-alpha channels and per-flush colour-cache isolation (LENS_FLARE_ONLY / REVIEW_ONLY)

- DATE=2026-10-28 KST; RUN_KEY=LENSFLARE-MATERIAL-ALPHA-SPLIT-20261028-0528; TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus; SOURCE_HEAD=2e5ad2f44c62c2fa269882481a11be77388c7cbb; SOURCE_SSOT=GITHUB_PINNED.
- BASELINE=R26+HUD 0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE; R84=COMPARISON_ONLY; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN; MODE=DX9EX_REVIEW_ONLY; SCOPE=LENS_FLARE_ONLY.
- INHERITED=CONVERSION-DX9EX-01529/01530/01535/01537/01539/01540/01541; LENSFLARE-FLICKER-ALPHA-20261027-2204; LENSFLARE-ALPHA-COMPOSITOR-20261028-0201. DISTINCT_AXIS=the actual +0x0C versus +0x44 PMT colour-record channels and the 408AF0 cache reset on each original opaque flush. Prior 0201 traced source alpha into native material processing, but did not distinguish the two offsets or prove that a second successful 570008 flush cannot simply inherit the first flush's material colour-cache key.
- EVIDENCE_KIND=PINNED_SECONDARY_ORIGINAL_GAME_RECONSTRUCTION_PLUS_CURRENT_MOD_GITHUB_READ; ORIGINAL_RETAIL_EXE_BYTES=NOT_REVERIFIED; LIVE_PMT_TEXTURE_OR_SHADER=NOT_CAPTURED; GPU_PIXELS=NONE; HMD=NO; CI_SKIP=NONE; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED.

## NEW_FINDING — bounded original material-alpha lineage; no optical root-cause claim

NEW_FINDING=STATIC_ORIGINAL_4056D0_DIFFUSE_ALPHA_OFFSET_0C_IS_DISTINCT_FROM_410DD0_COMBINER_ALPHA_OFFSET_44_AND_EACH_NONEMPTY_405890_FLUSH_RESETS_MATERIAL_COLOUR_CACHE.
CONFIRMED_DOUBLE_FLARE_HEAD_LOCK_DEPTH_ROOT_CAUSE=NONE; ACTUAL_LENS_PMT_ALPHA_SHADER_EFFECT=UNVERIFIED; CURRENT_HMD_REGRESSION=UNPROVEN.

1. Original reconstructed `Sun::flare_40c9a0` calls `Sun::draw(handle,intensity*k)` for both intended CABE `0x570008` ordinals. `render_object_override_4056d0` loops over *all* colour records and overwrites each record's `+0x0C` float with that value, while saving the previous word for 4052C0 undo. In the 0x48-byte PMT material-colour record this is `m[3]`, the diffuse alpha. It does **not** overwrite `+0x44` (`m[17]`).
2. Original `material_colours_410dd0` reads all 18 floats: `vsc(0x12,m+0,1)` forwards `m[3]` as the W component of a vertex constant; if `ambient_pass`, pixel constant 0 likewise receives `m[3]`. **Separately**, `alpha=((m[17]+1)*0.25)*px.alpha_scale*255` is clamped to [1,255] and sent to `combiner_constants_40b4b0(0,4,a8<<24)`. Thus the per-source alpha override and the combiner alpha constant have *different* original-record inputs. A zero CABE `intensity*k` does not itself prove the latter constant is zero, nor does a nonzero source alpha prove a visible pixel: the PMT shader, texture alpha, blend, colour mask, geometry and actual Draw still decide.
3. `material_408c80` can skip `material_colours_410dd0` when `mc.colour_index` and `mc.object_key` match the preceding draw. However `Flush::flush(405890)` calls `begin_408af0` for every **nonempty** queue, and that begin resets `mc.colour_index=None`, `mc.object_key=0`, and texture keys. Therefore a successfully submitted second `0x570008` in a separate 405890 flush does not merely inherit the *previous flush's* colour-cache key. This does not exclude material-cache reuse **within** one flush, failed admission, or shader-specific alpha interpretation.
4. In original `sun_flare_40cbc0`, ordinal #1 `0x570008` precedes explicit `render_queue_flush_4052c0`; that flush drains the opaque queue, undoes colour overrides and sets `immediate_8999b0=1`. Ordinal #2 then re-enters `4056D0` with its independently computed `glow` value and normally triggers a separate immediate 4052C0/405890 flush. For a **nonempty, successful physical second flush**, `begin_408af0` refreshes the material colour cache before its PMT draw. This rules down *cross-flush stale colour-cache reuse* as a sufficient explanation for a wrong second glow alpha on the reconstructed normal path.
5. The first `0x570008` uses `flare` and the second uses `glow`; the flicker branch can zero the former while retaining the latter (2204). This review does **not** assert both actual pixel alphas, that the same texture material is selected, or a second erroneous emitter. The current mod `src/hooks_graphics.cpp::DrawObjectAlphaProjected` logs original source `alpha` before 4056D0, not PMT `m[17]`, combiner constant, pixel shader output or eye RT. R30's sampled physical CLASS/EYES receipts still lack opaque descriptor/PMT/material identity. No live same-frame join is present.
6. The inspected original code is an independent reverse-engineered reconstruction, not a new retail EXE byte comparison. Current focus mod source `src/hooks_graphics.cpp` blob `640e0438f82922f5488770c46451caa712bfbde1` and `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` blob `400664d0740e86a9a29181d6f1954eb90ec549d2` are unchanged from 01541. This is a narrower diagnostic negative control, not evidence of a newly introduced DX9Ex renderer regression.

## SOURCE_TRACE (one-based pinned GitHub source)

- ORIGINAL `r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62/src/platform/race_course_passes.cpp` blob `22985e118c172467c566fe58d5b08f280c565ee2`: `Sun::draw:431-437`, `Sun::flare_40c9a0:441-458`, `sun_flare_40cbc0:687-715` (flare/glow and two 570008 calls).
- ORIGINAL `src/platform/pc_render_queue.cpp` blob `95e5709c69e22b5bee653786c85b86024e6fc9d1`: `render_object_405360:219-246`, `render_object_override_4056d0:288-305` (+0x0C override and undo).
- ORIGINAL `src/platform/pc_render_flush.cpp` blob `e6928a316ee4d503910cbe970b26f137e41c158e`: `begin_408af0:186-194` (cache reset), `material_colours_410dd0:293-325` (m[3] vs m[17] split), `material_408c80:665-718` (material colour-cache gate, textures), `Flush::flush:810-820` (nonempty queue begin), `render_queue_flush_4052c0:970-980` (undo/reset).
- CURRENT `thp32tt/OutRun2006Tweaks@2e5ad2f44c62c2fa269882481a11be77388c7cbb/src/hooks_graphics.cpp:731-793` (sampled source alpha, scoped CABE); `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5500-5547,5683-5777` (unlinked physical candidate and conditional eyes). R26+HUD baseline untouched.

## HYPOTHESIS_LEDGER / FALSIFICATION

| ID | Status and falsifier |
| --- | --- |
| A extra original emitter | OPEN. Two 570008 source ordinals are intentional; colour-cache state cannot add a source call. Confirm only excess per-sun source call AND matched unexpected same-eye colour pixels. |
| B opaque/D3DX/native replay | OPEN / PHYSICAL_JOIN_MISSING. Each original 405890 pass may include multiple legitimate primitive/material Draws. Require same descriptor+primitive+pass+material+eyeRT colour-write fingerprint more than once beyond expected. |
| C wrong WVP/c64 and L/R depth | OPEN. A colour-record alpha split cannot fix/confirm first CABE SceneEffect versus second projected WVP, raw-c64 shader-epoch mismatch, or incorrect eye FOV. Join source c64, R30 class, actual L/R WVP and fresh XR pose. |
| D intended alpha/texture overlap | NEW_STATIC_SPLIT: `+0x0C` source diffuse alpha and `+0x44` combiner input are distinct. Cross-flush colour-cache carryover is ruled down **conditional on both actual nonempty flushes**. Need actual material index, texture, m[3], m[17], px.alpha_scale, PS combiner, blend and RGB pixels to establish D as visual cause. |
| E host extra/cached projection | Prior standard one-layer / cached-pose controls remain; material constant differences are upstream of XR. Compare same fresh game Present and final xrEndFrame two-eye RGB and layer flags. |
| F head-lock / source-camera yaw | OPEN. Alpha changes may shift the perceived centroid but cannot establish world-locked yaw response. Test matched game blended-eye/View140, latched pose, same-RT pixels under yaw and translation negative control. |

## EVIDENCE_GAPS

- No original retail PMT colour/texture bytes for the installed `0x570008`; no verification of `m[17]`, material `colour_index`, `px.alpha_scale`, shader/combiner selection, 4056D0 admission, 4052C0 nonempty physical flush, primitive/pass actual Draw, RGB write or HMD observation.
- The reconstruction is not a verified binary-equivalent oracle. A zero `m[3]` can still suppress pixel alpha in a particular shader even when the separate combiner constant remains nonzero; conversely a nonzero `m[3]` may still rasterize no pixels.
- No joined original source-call serial -> opaque descriptor/flush -> native shader/PMT pass -> left/right RT -> host fresh/cached OpenXR frame.

## FALSIFICATION / NEXT_REVIEW

- POSITIVE_CONTROL: same sun invocation, both CABE 570008 admissions, first `intensity*flare` and second `intensity*glow`; read material record `m[3]` and `m[17]` at each 405890, confirm `begin_408af0` reset, material constant writes, nonempty PMT Draw, per-eye RGB and fresh XR source frame. When m[3] changes but m[17]/px.alpha_scale stay fixed, combiner a8 must stay fixed on the reconstructed formula; test actual shader output separately.
- NEGATIVE_CONTROL: no second PMT draw, skipped 4056D0, empty queue, or material shader never consumes m[3] => cannot infer visible alpha from source. If actual second 405890 starts with stale colour cache despite a nonempty flush, the reconstructed 408AF0 assumption is contradicted and needs retail-byte revalidation.
- NEXT_REVIEW=LENS_FLARE:VERIFY_570008_ORDINAL1_2_PMT_COLOUR_RECORD_PLUS0C_VS_PLUS44_COMBINER_TEXTURE_BLEND_AND_SAME_FRESH_LR_RT_PIXELS.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=NONE. Do not alter alpha, material caches, suppress either 570008, or change eye WVP until actual native PMT/texture/pixel evidence identifies a defect. Any future fix must be lens-material-specific, reviewable against protected R26+HUD, and separately HMD-tested; R84 remains comparison-only.
- REGRESSION=HIGH_IF_PREMATURE: changing source alpha or shared combiner may remove intended glow/occlusion or break unrelated PMT materials; a source call is not an actual colour-writing Draw, and two intended eyes are not duplicate same-eye pixels. Never add B9200 post-CALL/+5 hooks.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE.
