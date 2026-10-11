# Rework convergence rules (2026-10-08)

## 2026-10-11 전 레인 글자별 크기 검수 규칙 (최신 사용자 지시)

**적용 대상:** A/B/C1 제작·자체 QA, C2 독립 최종 QA, C3 엄격 QA, CLEAN 이후 렌더·저장 DDS 시각검수, PRE_INGAME 및 재작업 판정 전부. 원문과 번역의 언어/글자 수가 다르다는 이유로 한글 문장 전체 가로세로 비율·폭 점유율·영문 픽셀 면적/실루엣 일치율이 다르게 나온다는 것은 **반려 사유가 아니다**. 이 지시가 과거의 "undersized/underfill/원문 길이·폭에 비례/가능한 크게" 문구보다 우선한다. 자세한 단일 정본은 `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`.

**판정:** 원문 개별 텍스트/줄의 정확한 글자+효과 bbox를 넘는 한글 픽셀은 1px도 허용하지 않는다. 그 안에서는 한글이 원문보다 더 좁거나 작아도 허용하고, 원문 총 문장 길이나 글자 개수/캔버스 비율을 맞추기 위해 확대하거나 가로 늘이지 않는다. 비교 대상은 실제 한글 **글자 하나하나**의 네이티브 높이/획 굵기/받침·내부 공간/윤곽·효과·가독성과 UI 계열의 대표 원문 글자 크기·위계이다. 영문과 한글 글자 수가 달라 1:1 대응시킬 수 없으므로 'n번째 영문 글자 = n번째 한글 글자' 강제 매칭도 금지한다. 번역이 더 짧은 **그 사실 자체는 PASS** 처리한다.

**반려 가능 조건:** 원문 bbox 초과, 겹침·보호 아트 변경·잘림, 한글 오탈자/획 손상/실제 읽히지 않음, 명백한 서체·기울기·효과 오류는 각각 구체적 원인과 실제 픽셀 증거가 있을 때만 FAIL. 기존 `UNDERFILL`/`SOURCE_WIDTH_RATIO`/`WIDTH_RATIO`/`WHOLE_SENTENCE_ASPECT`만 근거인 REWORK는 현행 글자별 시각검수에서 **크기 조건 PASS로 재분류**하고 나머지 QA 통과를 확인한 뒤 정상 C2/C3 경로로 진행한다. 미검수 자료를 근거 없이 전체 승인으로 바꾸거나 사용자 실게임 OPEN을 닫지 않는다. `RUNTIME_VALIDATION=UNTESTED` 유지.


A/B selection should use `python tools/localization/rework_triage.py --index N` after refreshing Git. `EVIDENCE_ONLY_HOLD` means gather missing visual proof against unchanged DDS bytes; it does not require a new DDS. `FRESH_C_REVIEW` means independent C inspection. `VALIDATION_ONLY` means current evidence and actual in-game retest are still necessary. `MATERIAL_REWORK` means correct the failed construction stage.

`METHOD_CHANGE_REQUIRED` means two distinct recorded C rejections share a visual root-cause family. Do not repeat the previously rejected technique. First measure a source-derived profile (native reference, readable slant, proportions, stroke weight, plate continuity, outline, shadow, gradient, and RAW view), then materially change the renderer or use manual reconstruction. Re-run producer QA, independent C/C3 and real game retest. Record specific review evidence in `localization/graphics/REWORK_ESCALATIONS.json`; never invent past rejections.

`PRESERVE_ORIGINAL` is not a Korean DDS production target. This triage is read-only and cannot mark PASS, close an in-game defect, or change A/B/C1/C2 scheduling. Completion reports must distinguish produced DDS, current evidence-backed approval, remaining user-visible defect and actual game validation. Repeat inspection of unchanged SHA without new evidence is not additional completed work.

A/B/C controller entrypoints should read this document before choosing a rework item. Apply the triage against the latest branch queue, without bypassing the evidence gate.

## Root-cause-directed reconstruction and clean-plate failure taxonomy

Classify *where* the visual failure originates before choosing another DDS
render. Each code requires concrete pixel/source evidence in the existing
queue/role QA report; do not infer defects from historical text alone.

| Failure / explicit code | Reopen at | Required material change |
| --- | --- | --- |
| `SOURCE_RESIDUE_UNDER_KOREAN` | Source removal + PLATE_ONLY | Restore English glyph, outline and glow footprint; Korean cannot conceal ghosts |
| `INCOMPLETE_CLEAN_PLATE` | CLEAN_PLATE | Restore uninterrupted source plate/gradient/alpha/textured detail, not a flat patch rectangle |
| `FOREIGN_BOX_ARTIFACT` | Composition | Remove foreign image/UI pixels from crop; paste only justified transparent glyph/effect alpha |
| `BACKGROUND_PATCH_INTRUSION` | Plate/composition | Restore donor/target source relationship and protected pixel continuity |
| `RECTANGULAR_COMPOSITE_TRACE` | Composition | Eliminate visibly changed rectangular crop seam or luminance/alpha block |
| Flat/unsupported added shadow, outline or red bevel | Family renderer | Match source flat layers; remove arbitrary offset/shadow rather than increasing effects |
| Wrong individual-glyph shape/legibility, genuine line hierarchy, slant, chrome or gold bevel | Source family | Compare individual glyph contours/strokes and actual readability with a native English UI-family reference; translation-dependent sentence width/aspect/underfill alone must PASS the scale criterion |
| BC/DXT compression pinholes/dotted strokes | DDS encoding | Verify persisted decoded face/alpha and source format/MIPs before fresh C |

A producer may use a rectangular **selection tool** or mask bounds internally;
only its visible unauthorized changes are defects. Do not mark a correct image
as FAIL solely because the editor used a rectangular selection.

All new/materially reworked candidates must pass separately:
(1) **SOURCE vs CLEAN** with Korean hidden; (2) **CLEAN vs FINAL**
showing glyph/effect-only authorized differences; and (3) SOURCE vs
persisted decoded FINAL for family fidelity at native, 100/75/50 sizes,
RAW/readable and authored MIPs. If stage 1 fails, halt text rendering and
repair CLEAN first. If stage 2 fails, fix composition without rebuilding
a good glyph unless genuinely necessary.

Before propagating a generator to other members of one family, C must inspect
one representative persisted candidate. For evidenced repeat
`METHOD_CHANGE_REQUIRED`, the next attempt must cite the specific new
source-conditioned construction profile and describe how it differs from
the rejected technique. q172/q214 source metallic-bevel and q175/q219
chrome/UI-family problems must not become repeated flat/SDF/shear recolor
attempts. If original contour/profile cannot be matched safely, record
`MANUAL_RECONSTRUCTION_REQUIRED` and let the other A/B shard proceed on
unblocked work; do not pass a knowingly defective candidate downstream.

**No QA inflation:** `EVIDENCE_ONLY_HOLD` is not an A/B production task;
historical C3 remains historical. Report separately actual new DDS, new
independent C acceptance, active rework, repeated-cause failures,
evidence-backed approval, user test-build candidates and true in-game
acceptance. A `USER_REVIEW_NOT_APPROVED` package enables feedback before
final export and never upgrades current QA state by itself.

## Production-stage enforcement — 2026-10-09

Apply `docs/KOREAN_LOCALIZATION_PRODUCTION_RESET.md`: family-pilot WIP limit,
pinned recipes, first-failed-stage repair, two same-method trials maximum,
source-protected versus previous-candidate write checks and producer pixel guard.
Missing-only evidence must not trigger rerender; new failures must not reset the
same-method retry history. A family-scoped pilot review is not whole-atlas approval.
