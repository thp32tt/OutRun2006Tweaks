# OutRun 2006 한글화 실패 원인과 생산 계획 수정 제안 — 2026-10-11

**상태: REVIEW_PROPOSAL_ONLY / NOT_APPLIED.** 이 문서는 새 생산 정책의 시행·QA 승인을 선언하지 않는다. 기존 `KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`, `KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`, A/B/C1/C2/C3 소유권, P0/P1, 원본/PLATE 증거 게이트, 사용자 인게임 최종 확인이 우선한다. VR/FFB/DX11/DXVK 제외.

## 기준 자료 및 현재 관찰

- 기준 브랜치 `korean-localization-recovery-20260928`, 분석 시작 HEAD `e8686fa52f6305e55ebb5fdc04d1df5baba5793c`. 후속 동시 커밋이 있을 수 있으므로 실행 전 최신 HEAD를 재조회한다.
- `localization/graphics/asset_queue.csv`: 137행. 상태 문자열에 REWORK 33행, PASS 문자열 47행, HOLD 9행, PRESERVE 46행, 기타 2행. 이는 **현재 승인 수가 아니다**. 전체·현재 후보 SHA·C2/C3·게임 게이트를 반드시 따로 센다.
- `localization/graphics/INGAME_REWORK_BACKLOG.csv`: 60개 보고(P0 28, P1 32; GRAPHICS 44, MIXED 12, RUNTIME_TEXT 4). 결함 태그는 중복 허용: LOW_RES_FONT 31, BAD_SLANT 11, SOURCE_RESIDUE 6, TEXT_OVERLAP 6, PLATE_RECONSTRUCTION_DIRTY 4. `OPEN_USER_INGAME_FAIL` 상태 19행; 그 외도 신규 실게임 재검 미완료가 많다.
- `localization/resume_state.json`의 2026-10-11 최근 기록: q121 A241/A242는 정본 콜론/윤곽 개선 후에도 원본 곡선형 이탤릭 불일치로 미승격; q193 A243/C2는 단일 셀 scoped PASS지만 전체 아틀라스 HOLD; q060 B370-373 ImageGen은 대시보드 혼입·콜론 누락·서체 불일치, B373 생성 원본 PNG 미게시/시험 DDS 0; q102 C1 ImageGen은 다른 문구·원본 chrome 효과 불일치, 생성 PNG GitHub 미게시/시험 DDS 0.
- `tools/localization/imagegen_b_pipeline.py`의 `dds_rgba_read`는 mip 0/1, bpp=32 및 비압축 128바이트 DDS만 수락한다. q102처럼 BC3/DXT5인 자산은 consumer에서 fail-closed. **기능 공백을 프롬프트 개선으로 해결할 수 없다**.
- `localization/graphics/REWORK_ESCALATIONS.json`: q060 원문 잔상, q172/q214 입체·베벨, q219 크롬 원본 계열 불일치는 동일 크기/기울기/색 조정 반복으로 수렴하지 않았다. q048은 보호된 청록 장식 415픽셀 원본→CLEAN 손실이 독립 검출됐다.

## 실패 원인의 우선순위

1. **생산물 이송/인코딩 경로 결손:** 실제 ImageGen 성공도 원본 PNG binary + 생성 provenance가 GitHub에 게시되지 않으면 소비자 DDS 입력이 없고, BC3는 현 consumer가 읽지 못함. 생성 건수와 DDS 생산 건수를 혼동하지 않는다.
2. **원본 스타일 재현 실패:** 한글 획의 곡선, 네이티브 굵기·속공간, 기울기, 크롬 층·금속 베벨이 원문 계열과 다름. 기계적 bbox/ROI 통과는 이 실패를 감지하지 못함.
3. **CLEAN/복합 아틀라스 오염:** 영어 원문 그림자 잔재·보호 장식 소실·직사각형 합성 흔적·이웃 셀 침범. 과거 한글 후보를 CLEAN 정본으로 쓰면 결함이 누적된다.
4. **생성 지시의 참조 오염·정확한 문구 미보장:** 비교 JPG/대시보드가 생성물로 나옴, 다른 한글·구두점 누락, 투명 PNG만 필요할 때 전체 장면 생성. 2026-10-11 신설 `KOREAN_LOCALIZATION_IMAGEGEN_PROMPT_GUIDE.md`는 필요한 정책이지만, 새로운 이미지→DDS→C2 수락 실증 전이므로 효과가 검증됐다고 간주하지 않는다.
5. **재작업 반복과 범위 혼합:** 재시도 간 새로운 원인 수정 없이 크기/색/모양만 바꾸고 동일 실패를 반복. 단일 셀 scoped PASS와 전체 아틀라스 PASS, 정적 C2/C3와 사용자 실게임 종결을 혼동하기 쉬움.
6. **지난 폭 기반 반려의 정책 충돌:** 2026-10-11 `GLYPH_SCALE_POLICY`에 따라 번역문 전체 폭·길이 차이는 독립 FAIL 근거가 아니다. 대신 네이티브 **개별 글자** 가독성/굵기/내부 공간/원본 UI 계열 스타일을 증거로 판정해야 한다.

## 수정 제안: 생산 게이트와 실행 순서

### G0. ImageGen 채널 사전 검증 — 생산 확대 전 선행 (P0 기술 과제)
- 원본 DDS의 native format, mip, RAW/FLIP-Y, canon SHA 및 정확 source bbox를 자동 확인한다. 대상 형식을 처리할 엔코더가 없으면 ImageGen 호출 자체를 **`FORMAT_BLOCKED`**로 보류한다.
- ① 최소 영문 원본 crop만 생성기에 입력 ② 실제 투명 RGBA 단일 문구 PNG 확보 ③ 원본 PNG bytes·SHA·생성 ID·정확 프롬프트를 ChatGPT 로컬에 보존 ④ GitHub binary 업로드 ⑤ 원격 bytes 재다운로드 SHA 일치 ⑥ 기존 consumer trial DDS 산출의 **왕복 소형 대표 실험**을 먼저 통과시킨다. 업로드 미완료라면 `PNG_NOT_PUBLISHED`로 종료하고 시도 횟수를 DDS 수에 넣지 않는다.
- BC3/DXT5 consumer를 별도 경로로 지원한다. Microsoft DirectXTex/texconv `BC3_UNORM` 사용은 기술 후보이나 실수정 가능 여부는 시험해야 한다. 구형 게임의 원래 DDS 형식/헤더/mip 수/방향을 보존하고 원본과 동일한 보호 4x4 블록은 원본 압축 블록을 유지하는 방식을 검토한다. 경계 4x4 블록이 보호 픽셀에 영향을 주면 FAIL, 무조건 전체 아틀라스 재압축·무조건 RGBA32 변경 금지.

### G1. CLEAN과 정확 정본 (재생산 전)
- 원본 SOURCE→CLEAN 단독 픽셀/시각 증거 및 독립 C2 PLATE_PASS가 없으면 글자 생성 보류. q060 승인된 plate는 정확 SHA에 한해 재사용; q102는 판정 전 합성 중지.
- 정본 한국어 문구/구두점/남겨야 할 영문/원문 글자 bbox/모든 이웃 셀의 보호 마스크를 한 레시피에 고정한다. 런타임 텍스트(IGR042)는 무턱대고 DDS 수정 대상으로 매핑하지 않는다.

### G2. 계열 대표 생산 (A 독립, B/C1 ImageGen 독립 유지)
- A는 기존 native/vector/manual, B는 신규 미할당 짝수 index%4=0, C1은 신규 미할당 짝수 index%4=2, C2는 전 레인 독립 검수. 현재 진행·명시적 P0/P1 소유권 보존.
- 계열 `small_HUD / gray_menu / rounded_italic / red_condensed_title / layered_gold / chrome_metal`별 **검증되지 않은 제작법당 대표 1개**만 시험한다. 난도 낮고 이미 PLATE_PASS된 ImageGen 후보 1개로 G0 E2E를 먼저 실증하면서 현재 소유 P0는 별도 추적한다.
- 생성기는 QA 패널이 아닌 source text 단일 crop을 참조, 정확 한글 글자층 하나만 출력. 글자 판독/구두점/진짜 알파/서체·기울기·레이어 스타일을 **DDS 인코딩 전에** 원본과 나란히 검수한다. 출력이 대시보드, 오문구, 스타일 불일치면 이미지 단계에서 FAIL, 불필요한 DDS 생성 금지.
- 가로 폭·원문 영문 문자 개수와 1:1 맞추기 금지. 원본의 **글자+효과 영역 1px 초과는 FAIL**, 그 안에서 문구가 더 짧은 자체는 PASS. 가독성·자소·원본 스타일의 실측 근거로만 미흡 판정.

### G3. DDS/독립 QA/게임 검증
- `SOURCE → CLEAN → LETTERING → FINAL → persisted DDS → RAW/FLIPY/100·75·50%/MIP → C2 → C3 → user in-game`을 한 SHA로 묶되 각 게이트를 독립 기록한다.
- `production_pixel_guard.py`의 원본→CLEAN/원본→FINAL 보호영역 비교, 1px 초과·원문 잔상·다른 UI 훼손 검사 유지. 기계적 PASS가 원본 스타일/실게임 PASS를 대체하지 못한다.
- 대표 C2 **최초 수용** 전 동일 서체/플레이트 제작법을 다수 후보에 복사하지 않는다. C2 `SCOPED_PASS`는 그 셀만 인정, 전체 아틀라스 나머지 셀과 C3/게임은 OPEN.
- 사용자 P0 실게임 실패는 정확 수정된 신규 DDS와 테스트 빌드·재캡처를 확인할 때만 종결한다. 실제 인게임 미수행 시 `RUNTIME_VALIDATION=UNTESTED` 유지.

### G4. 실패 수렴 및 집계
- 동일 원인의 동일 방법 조정은 최대 **2번**, 재시도 사이 호출이 바뀌어도 계속 누적한다. 2차 독립 동일 원인 실패 후 `METHOD_CHANGE_REQUIRED`, 원본 계열 레시피/PLATE/압축/프롬프트 입력 중 **무엇을 바꾸는지** 먼저 제시하고 다른 안전한 작업으로 이동한다.
- QA 거절은 `FORMAT_BLOCKED / PNG_NOT_PUBLISHED / EXACT_TEXT / CLEAN / FONT_MORPHOLOGY / SLANT / METAL_EFFECT / DDS_PIXEL / EVIDENCE_ONLY_HOLD / RUNTIME_RETEST` 등 **최초 실패 단계** 별로 분류한다. 누락 근거를 새 한글 이미지 생성으로 고치지 않는다.
- 주간/작업별 KPI: ImageGen 시도 수, exact-text 투명 PNG 수, **원격 게시된 PNG 수, 실제 저장 trial DDS 수, 최초 C2 수용률**, 같은 결함 반복률, 현재 whole-atlas C2+C3 승인 수, 사용자 실제 게임 종결 수를 별개로 센다. C2 PASS 없는 trial DDS와 정책 변경 자체를 완료 DDS로 세지 않는다.

## 수용 기준과 바로 다음 검증

1. **PNG 전달 경로 시험**: 신규로 생성한 유효 투명 PNG 하나의 GitHub 원격 SHA와 로컬 SHA 일치.
2. **DDS 인코딩 시험**: 실제 q102 BC3 또는 동형 대표에 대해 기존 포맷/헤더/mip/방향 보존, 압축 경계 포함 보호 픽셀 0 손실, 100/75/50% 가독성 증명. 불가능하면 BC3는 보류하고 호환 대상부터 시험.
3. **수용성 시험**: q060과 q102는 각 기존 원인별 ImageGen P2 재검, A q121은 새 glyph-family 기준 C2 검수. 시각적 기계 PASS만으로 승격 금지.
4. **메트릭 검증**: q193 `15 연속전` scoped PASS는 유지하되 남은 셀과 전체 아틀라스 승인 분리. 폭 비율 **단독** 실패 이력은 최신 개별 글자 정책으로 재검하며 다른 실제 결함은 계속 REWORK.
5. **변경 승인**: 이 검토 문서를 기반으로 자동 컨트롤러/파이프라인/계약 실행 규칙을 **별도 구현 및 테스트**한다. 아직 기능 구현, 새 DDS, C2/C3 통과 또는 실게임 결함 종결은 이 문서만으로 발생하지 않는다.

## 1차 근거
- `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`
- `docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md`
- `docs/KOREAN_LOCALIZATION_PRODUCTION_RESET.md`
- `docs/KOREAN_LOCALIZATION_IMAGEGEN_PROMPT_GUIDE.md`
- `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`
- `docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md`
- `localization/graphics/asset_queue.csv`
- `localization/graphics/INGAME_REWORK_BACKLOG.csv`
- `localization/graphics/REWORK_ESCALATIONS.json`
- `localization/resume_state.json`
- `localization/progress/progress.json`
- `tools/localization/imagegen_b_pipeline.py`

**외부 기술 참조:** `microsoft/DirectXTex` 공식 `texconv` 문서의 BC3/DXT5 지원. 형식 지원이 곧 본 게임 DDS 로드·무손상 호환 보증을 뜻하지 않는다.
