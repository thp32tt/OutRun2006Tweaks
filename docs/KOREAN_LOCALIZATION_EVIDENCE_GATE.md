# Evidence-backed production and approval — 2026-10-08

## 2026-10-11 전 레인 글자별 크기 검수 규칙 (최신 사용자 지시)

**적용 대상:** A/B/C1 제작·자체 QA, C2 독립 최종 QA, C3 엄격 QA, CLEAN 이후 렌더·저장 DDS 시각검수, PRE_INGAME 및 재작업 판정 전부. 원문과 번역의 언어/글자 수가 다르다는 이유로 한글 문장 전체 가로세로 비율·폭 점유율·영문 픽셀 면적/실루엣 일치율이 다르게 나온다는 것은 **반려 사유가 아니다**. 이 지시가 과거의 "undersized/underfill/원문 길이·폭에 비례/가능한 크게" 문구보다 우선한다. 자세한 단일 정본은 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`.

**판정:** 원문 개별 텍스트/줄의 정확한 글자+효과 bbox를 넘는 한글 픽셀은 1px도 허용하지 않는다. 그 안에서는 한글이 원문보다 더 좁거나 작아도 허용하고, 원문 총 문장 길이나 글자 개수/캔버스 비율을 맞추기 위해 확대하거나 가로 늘이지 않는다. 비교 대상은 실제 한글 **글자 하나하나**의 네이티브 높이/획 굵기/받침·내부 공간/윤곽·효과·가독성과 UI 계열의 대표 원문 글자 크기·위계이다. 영문과 한글 글자 수가 달라 1:1 대응시킬 수 없으므로 'n번째 영문 글자 = n번째 한글 글자' 강제 매칭도 금지한다. 번역이 더 짧은 **그 사실 자체는 PASS** 처리한다.

**반려 가능 조건:** 원문 bbox 초과, 겹침·보호 아트 변경·잘림, 한글 오탈자/획 손상/실제 읽히지 않음, 명백한 서체·기울기·효과 오류는 각각 구체적 원인과 실제 픽셀 증거가 있을 때만 FAIL. 기존 `UNDERFILL`/`SOURCE_WIDTH_RATIO`/`WIDTH_RATIO`/`WHOLE_SENTENCE_ASPECT`만 근거인 REWORK는 현행 글자별 시각검수에서 **크기 조건 PASS로 재분류**하고 나머지 QA 통과를 확인한 뒤 정상 C2/C3 경로로 진행한다. 미검수 자료를 근거 없이 전체 승인으로 바꾸거나 사용자 실게임 OPEN을 닫지 않는다. `RUNTIME_VALIDATION=UNTESTED` 유지.


Policy version: `visual-evidence-v1-20261008`. This is quality evidence, not a new scheduler.
The existing six launches/hour and A/B/C1/C2 ownership remain unchanged. Three assets
per C invocation is an upper bound, never a reason to abbreviate inspection.

## 2026-10-09 user screenshot gate on QA previews

New actual-game visual failures override historical C3 eligibility on the
*same exact asset*. A USER_REVIEW_NOT_APPROVED preview must exclude indexes
with `OPEN_USER_INGAME_FAIL` in INGAME_REWORK_BACKLOG.csv even if the
queue is stale and claims C3. Emit USER_REVIEW_EXCLUDED_INGAME.csv to show
which candidates were withheld; preserve their bytes and QA history.
Always keep separate counts of historical C3 preview candidates, excluded
user failures, current evidence-approved graphics and user-accepted
real-game assets. Missing mapping is not grounds for guessing the DDS.
For closure, require the new candidate/runtime exact SHA, native
SOURCE/CLEAN/FINAL 100/75/50 + RAW/FLIP-Y inspection, and new actual-game
screenshot test. Static numerical PASS cannot promote an open user failure.

## Immediate execution order

1. C1/C2 first calibrate their visual review using a normal control plus known rejected
   opposite-slant, clipped-stroke, residue and excessive-weight examples. Reuse exact
   historical defect crops where available. If a control is missing, create and label
   an intentionally defective variant of a source-faithful reference. Keep the answer
   key separate until first-look decisions have been recorded. Never call these
   synthetic variants production candidates. A missed defect blocks PASS, not repair work.
2. Prioritize current user regressions and q154 gray-menu counter-space/weight recheck
   in its C2 shard. Compare native decoded DDS before deciding REWORK versus PASS.
   The 2026-10-08 q154 finding is a contact-image suspicion, not an invented runtime test.
3. A/B repair assigned regressions and establish a representative source-derived
   profile for each menu/mission/rank/small-help family before propagating its renderer.
   C reviews the pixels before consulting producer PASS prose. Record that first look.
4. C3 makes a separate pass with its own review ID, eight observations per segment,
   prior-defect review and family comparison. The same controller may do this in a
   separate inspection pass; do not claim a different reviewer when there was none.
5. Export only current approvals accepted by `qa_evidence_gate.py`. Unknown evidence
   stays HOLD. Legacy records are history, not new-policy approvals. Do not rerender
   good DDS merely to migrate evidence; inspect the existing exact bytes instead.
6. User image acceptance and actual game acceptance remain separate. Only actual
   game evidence may close an in-game regression. DDS/screenshot package hashes must match.

## Producer measurement and evidence

- Use native source glyphs and padding before affine transforms. Preserve per-sprite
  RAW transforms separately from readable text slant. Do not decide lean by a variable sign.
- For each source and Korean region, record top-minus-bottom horizontal displacement
  in readable coordinates, anchor locations and a marked PNG. Opposite or accidentally
  upright lean fails. Ambiguous anchors are HOLD, not guessed zeroes. Compare magnitude
  visually against the source; no arbitrary universal angle tolerance is introduced.
- Retain pre-transform glyph, post-transform lettering and persisted-DDS decoded views
  to isolate clipping, font fallback, outline thickening and encoding damage.
- Preserve the original source bbox ceiling. Do not stretch Hangul to any percentage of English phrase width. Accept even substantially shorter Korean phrases and smaller individual glyphs if legible. Inspect native per-glyph height, stroke/counter clarity and visual hierarchy; phrase width/height/aspect differences alone are non-blocking.
- Inspect CLEAN without lettering first. Then inspect final native/high zoom/practical
  size, authored mips, RAW and readable views on black/white/gray backgrounds.
- `make_region_evidence.py` generates SOURCE/CLEAN/FINAL lossless crops from exact DDS.
  Its result is evidence-only; it does not fabricate PASS or inspect aesthetics.

Example (run from repository root, all inputs already materialized):

```sh
python tools/localization/make_region_evidence.py --source SOURCE.dds --clean CLEAN.png --candidate FINAL.dds --regions REGIONS.json --out localization/graphics/role_C/RUN/regions
```

REGIONS.json is a list of `{id, bbox: [left, top, right, bottom], readable_transform}`.
Boxes are native RAW coordinates; transforms are identity, flip_y, flip_x, rotate_180,
rotate_90 or rotate_270. Unsupported perspective/unresolved orientation requires
explicitly prepared evidence and a reviewed tooling extension; never silently normalize it.

## Dual-stage plate/composite evidence (producer and independent C/C3)

Before accepting a **new or materially changed** localized candidate, retain
two separately observed lossless pixel inspections, from the *same* exact
source and saved DDS candidate:

1. **PLATE_ONLY:** SOURCE vs CLEAN **without lettering**. Inspect canonical
   English glyph/effect removal including hidden shadow/glow; inspect uniform,
   gradient, texture, translucency, alpha edges and protected art. Record
   source/clean identities, crop PNG and PASS/FAIL/HOLD observation.
2. **COMPOSITE_ONLY:** CLEAN vs persisted decoded FINAL. Show the intentional
   Korean glyph/effect mask versus actual changed pixels and identify every
   background, alpha, protected-foreground and outside-mask delta. Record the
   crop PNG and PASS/FAIL/HOLD observation.
3. **STYLE/ORIENTATION cross-check:** canonical SOURCE vs FINAL at native,
   high zoom, 100/75/50-percent practical sizes, authored MIPs, RAW and
   readable view; compare source style family, slant, size/hierarchy, clipping,
   compression streaks and protected element integrity.

Evidence must distinguish at least these observed producer/C failure codes:
`SOURCE_RESIDUE_UNDER_KOREAN`, `INCOMPLETE_CLEAN_PLATE`,
`FOREIGN_BOX_ARTIFACT`, `BACKGROUND_PATCH_INTRUSION` and
`RECTANGULAR_COMPOSITE_TRACE`. Each visually confirmed defect is hard FAIL
even when outside-bbox changed-pixel count is zero; source/plate/effect-mask
uncertainty is HOLD, not guessed PASS. An editing tool's rectangular selection
is not itself a defect if it leaves no unwanted persisted pixel trace.

For **current-policy machine approvals**, retain these findings within the
already required per-region `clean_plate`, `placement`,
`protected_art`, `glyph_integrity` and `style` observations and their PNG
references, with the machine_report's authoritative changed-outside/protected
pixel counts. Do not add fabricated zeroes or call a prose-only check
machine-enforced. C/C3 must independently inspect actual images. The existing
`qa_evidence_gate.py` schema and exact-SHA requirement remain authoritative;
this clarification does not imply that new visual controls have already been
coded into that validator.

**Separate user-review artifact:** the deliberately unapproved
`USER_REVIEW_NOT_APPROVED` test package may include SHA-pinned historical-C3
candidates before user acceptance, so the user can perform real-game testing.
It remains outside PRE_INGAME current-policy approved export, cannot bypass
C/C3/current-policy evidence, cannot close runtime regressions without a new
matching in-game screenshot and must never be reported as an approved patch.

## Machine-enforced approval record

Store one current record per asset at `localization/graphics/role_C/APPROVALS/qNNN.json`.
Every referenced file uses `{path: repository-relative path, sha256: full SHA-256}`.
Paths must resolve inside this checkout. Binary changes invalidate bindings.

Required top-level fields:

- `policy_version`, `queue_index`, `asset_path`, `mode: localized`, `result: PASS`,
  `candidate_sha256`, `source_sha256`.
- `machine_report`: JSON reference with matching source/candidate hashes, `result: PASS`,
  and integer zero fields changed_outside, alpha_outside, protected_changed, overlap, clipping.
  Link original detailed machine evidence in that report; do not write unsupported zeroes.
- `clean_plate`, `decoded_final`: native PNG references. Export compares decoded_final
  pixel-for-pixel with the persisted DDS it actually loads.
- `segment_inventory`: JSON reference with source_sha256 and complete
  localizable_segment_ids. Resolve every source segment; preserve exclusions explicitly.
- `family_profile`: JSON reference with family_id, reference_observation and reference_image
  PNG reference. Retain source measurements and accepted reference hashes in the profile.
- `text_mips`: each DDS level in order, `{level, result: PASS, observation, evidence}`.
  Conservatively inspect all levels; the evidence is PNG and missing levels block export.
- `regions`: one entry per inventory ID, with id, native bbox, readable_transform,
  `slant: {source_top_minus_bottom_dx, candidate_top_minus_bottom_dx, anchor_observation}`,
  and `views`: native, zoom, practical, practical_75, practical_50, raw, black, white, gray
  mapped to PNG references. Include pre/post-transform construction references as well.
- `stages`: C and C3, each with review_id, reviewer, calibration reference and findings.
  C must record `pixels_before_producer_verdict: true`. C3 must record
  `prior_defect_observation`. Distinct review IDs are required, not fabricated reviewer identities.
- Each stage's findings maps every region ID to all eight checks: slant, clean_plate,
  style, readability, glyph_integrity, protected_art, placement, orientation.
  Each check records `{result: PASS, observation: actual finding, evidence: PNG reference}`.

Calibration JSON records policy_version, reviewer, blind_review_completed and cases.
Each case has kind (normal/opposite_slant/clipped_stroke/residue/excessive_weight),
image reference, observed (PASS for normal; FAIL for known defects), and observation.
This is a visual review record. Unit tests verify evidence enforcement only and MUST NOT
be copied into a calibration or claimed as successful visual defect detection.

Explicit original preservation instead requires mode: preserve_original,
candidate_sha256: empty string, source_sha256, policy_reason and policy_decision reference.
The decision JSON must bind queue_index/source_sha256 to decision: PRESERVE_ORIGINAL.
Missing DDS alone never implies preservation. A localized alias needs its own current
source/asset/segment binding, even when candidate bytes are identical.

## Export and progress

JPG is navigation/overview only. Authoritative evidence is the lossless per-region PNG
set. Export validates source identity, current bytes, calibration, checks and views;
string tokens in historical notes do not authorize anything. All localized exports use
this evidence gate so undocumented risk classification cannot bypass C3.

Run `python tools/localization/summarize_qa_state.py` before reporting progress and
after queue changes. Derive rework/HOLD/pending counts from the current status column,
not appended historical notes or old aggregate fields. Report production, declared
static PASS, evidence-backed export, user acceptance and in-game acceptance separately.

Historical pre-gate JPG exports are archived once under PRE_INGAME_JPG_REVIEW_ARCHIVE.
An empty current export during migration means evidence pending, not erased production.
Do not promote historical C/C3 PASS or claim runtime validation simply to restore counts.

## User in-game review before final graphics approval

The user cannot validate in-game pixels when export blocks **all** Korean DDS pending
user acceptance. Maintain two explicitly separate package stages:

- **USER_REVIEW_NOT_APPROVED:** A QA-preview artifact for a separate/backed-up game
  installation. The Windows test workflow copies the *same-commit* runtime and the
  current candidate bytes for queue rows with historical `c3_strict_pass` status.
  Its CSV lists exact DDS SHA-256, queue index and unapproved status. It excludes
  rows currently marked REWORK/FAIL/HOLD and missing candidate files. Historical C3
  is an eligibility heuristic for user inspection, not proof of current C3 approval,
  user acceptance or game correctness. Known defects can still surface.
- **EVIDENCE_APPROVED_GRAPHICS:** The independent package for final graphical
  approval flow. Every DDS must still satisfy `qa_evidence_gate.py` and current
  `role_C/APPROVALS/qNNN.json` evidence before it enters this package. The preview
  never modifies the approval list, queue state, calibration or runtime validation.
- **RUNTIME_ONLY:** With zero approved DDS, keep a current-head runtime debugging
  package instead of failing Windows compilation; it is not a graphics test package.

The user may test the unapproved preview **before** final approval and report queue
index, scene, screenshot and logs. A user-observed defect reopens the affected
graphics candidate under the existing in-game regression rules, regardless of
historical C/C3 labels. A user screenshot also does **not** automatically approve
untested assets or close other regressions. Production approval still requires the
current independent source/candidate evidence and actual game follow-up where
applicable.

No current-vs-historical build must be called a final Korean patch until all gates
are met. In progress reporting, give the three counts separately: historical C3
preview candidates, current evidence-approved exported DDS, user-tested/accepted
in-game assets.
