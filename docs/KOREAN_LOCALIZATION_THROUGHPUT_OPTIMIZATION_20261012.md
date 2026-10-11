# OutRun Korean localization production/QA throughput optimization — 2026-10-12

Scope: A/B/C1 production, C2 independent QA, C3 audit and user previews. This is an additive workflow refinement, not new ownership or automatic approval. Preserve the latest CONTRACT, QA_THROUGHPUT_POLICY and EVIDENCE_GATE.

## Verified bottlenecks

1. Many A/B trial DDS redo one unapproved texture. Count unique saved trials and whole-file approvals separately. Two independent failures of the same root-cause family require a new method, not repeated font recoloring.
2. For B/C1, a PSD/DDS-derived English-only transparent crop present on GitHub does not prove it was actually attached to ImageGen. SOURCE_REFERENCE_NOT_BOUND means no qualified generation, no Korean PNG, no new DDS. Stop before image generation.
3. Wrong Korean text, scenery, complete menus and opaque rectangles are not qualified transparent glyph layers. Reject before DDS conversion, keep rejected provenance.
4. ImageGen PNG fitting previously stretched separate horizontal and vertical axes under width_priority. Native fitting now preserves glyph aspect ratio, keeping exact source effects bbox as the hard ceiling.
5. C2 scoped static PASS is neither full DDS PASS nor C3 strict approval. Historical C3 queue labels are not current evidence-gate approval when fresh user-game defects remain OPEN.
6. Controller-suffixed OPEN_USER_INGAME_FAIL_... states remain open, not closed. Evidence gate must veto these as well.

## Producer and QA decision sequence

1. Read latest HEAD and canonical queue/backlog, then triage index N with python tools/localization/rework_triage.py --index N. Preserve A odd, B new mod4=0, C1 new mod4=2 and all explicit in-flight/P0/P1 ownership.
2. Reuse the exact SHA-pinned PSD and approved CLEAN, source crop and effect layers. A full PSD transparent composite is only a reference until pixel-matched to the canonical DDS and independently PLATE_PASS reviewed by C2.
3. On B/C1 require an actual attached English lettering-only transparent RGBA image and provenance receipt BEFORE any call. Do not retry image generation with an unbound source, and do not silently use manual font rendering as a B/C1 substitute. Record explicit blocker and switch to another READY owned item.
4. Qualify one representative candidate per source typography family. Check exact Hangul and clean alpha BEFORE running native DDS conversion. For A keep separate vector/face/rim/shadow layers.
5. Fit proportionally, never fill the whole source width by distorting letters. Source/CLEAN/glyph/actual persisted-DDS and RAW/FLIPY/100/75/50 checks remain hard requirements; check all protected atlas pixels and original effect bbox.
6. C2 first inspects new saved DDS SHA, active P0/P1, missing plate proof, then historical HOLD. Reuse previously verified exact-SHA region proofs; report inherited unreviewed cells and missing evidence in one bundle. Neither producer nor partial scoped verdict can self-approve a whole atlas.
7. After two independent same-cause material failures, change source family, PSD layer extraction, Hangul geometry or effects method. Alternatively process another READY index. Repeated same-method trials and repeated same-SHA QA do not add real completed work.
8. Keep C3 strict and user actual-game retest independent. OPEN user defects cannot close without testing newer repaired exact bytes. RUNTIME_VALIDATION=UNTESTED if not actually run.

## Metrics kept separate

- new_saved_dds: distinct Korean trial DDS, excluding English SOURCE/CLEAN DDS.
- imagegen_bound_attempts: actual image generation calls with verified attached English reference.
- imagegen_rejected_outputs: wrong target, scene or non-letter output.
- producer_scoped_pass: self-QA, not independent.
- C2_scoped_static_pass: independent partial region proof, not whole DDS.
- C2_whole_asset_pass: current saved SHA and all atlas cells approved.
- C3_strict_pass: independently reviewed strict stage.
- user_ingame_pass: actual game retest on newer repaired SHA.
- official_promoted: evidence-gated production DDS, not scratch output.
- open_user_ingame_fail: user OPEN reports, including suffixed state tokens.

Use python tools/localization/summarize_qa_state.py for read-only queue accounting. The approval_count value is null by design: only the exact-SHA evidence gate and real game records may establish actual approval. The new GitHub regression job tests the fit, scoped status and open-game veto without asserting visual or runtime PASS.

Never weaken wrong Hangul/foreign strokes, any 1px bbox overflow, clipping, English ghosting, plate seams, unrelated UI damage, codec/mip/decoded loss, or open user-game errors. Minor cosmetic differences or shorter Korean text alone do not require infinite retries.
